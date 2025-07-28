import copy
import gzip
import http.client
import json
import os
import uuid
import zlib

from pathlib import Path
from typing import Dict, Any, Type, Optional, List, Union, Set # Import Set

from pydantic import BaseModel, Field, create_model, ValidationError, validator

from invokeai.invocation_api import (
    BaseInvocation,
    BaseInvocationOutput,
    InputField,
    InvocationContext,
    OutputField,
    StringOutput,
    invocation,
    invocation_output,
    UIComponent,
)
from invokeai.app.services.config.config_default import get_config
from invokeai.backend.util.logging import info, warning, error

# Load the InvokeAI configuration to get the backend port:
app_config = get_config()

# Define the InvokeAI API host and path
# As confirmed by user, host is localhost:9090 for the API
API_HOST = "localhost"
API_PORT = app_config.port
API_PATH = "/api/v1/queue/default/enqueue_batch" # This part seems standard


class WorkflowProcessor:
    """
    The WorkflowProcessor is designed to bridge the gap between a raw InvokeAI
    workflow JSON and a user-friendly API for parameter adjustments.

    It performs three primary functions:
    1.  **Parsing:** Extracts relevant user-exposed input fields from the
        complex InvokeAI workflow JSON, specifically from the 'form' section,
        organizing them into an ordered, internally manageable structure.
    2.  **Schema Generation:** Dynamically creates a Pydantic `BaseModel` schema
        that defines the expected structure of user input. This schema is designed
        to be both simple for the user to provide and informative for developers
        to understand available fields.
    3.  **Input Application:** Takes validated user inputs and intelligently
        applies them to the correct fields within the workflow's graph nodes AND
        the workflow's node definitions, preparing the payload for submission
        to the InvokeAI backend.

    A key design choice is to support simplified user input (e.g., `{"value": 100}`)
    even when multiple nodes in the workflow might have fields with the same name.
    This is achieved by relying on the *relative order* of duplicate field names
    in the user's input list, matching them to the order in which these fields
    are defined within the workflow's 'form' section.
    """

    def __init__(self, workflow_json_payload: Dict[str, Any]):
        """
        Initializes the WorkflowProcessor with the InvokeAI workflow JSON.

        Args:
            workflow_json_payload: The complete workflow JSON received from InvokeAI.
                                   This payload contains the graph structure and
                                   definitions of user-facing fields within its 'form'.
        """
        self._workflow_payload: Dict[str, Any] = workflow_json_payload
        
        # _ordered_exposed_fields: An internal, ordered list of dictionaries,
        # each representing a user-exposed field parsed directly from the
        # workflow's 'form' section. This list maintains the definition order,
        # which is crucial for disambiguating fields that share the same 'fieldName'.
        # It correctly includes the user-facing label of the field itself.
        self._ordered_exposed_fields: List[Dict[str, Any]] = self._build_ordered_exposed_fields_list()

        # # --- DIAGNOSTIC PRINT ---
        # # This will show the exact order of fields that the processor has extracted
        # # from the workflow's 'form' section, including their user-facing labels.
        # print("\n--- Detected Order of Exposed Fields (Internal View) ---")
        # for i, field in enumerate(self._ordered_exposed_fields):
        #     field_label_part = f" (Label: '{field['field_label']}')" if field['field_label'] else ""
        #     print(f"[{i}]: field_name='{field['field_name_in_node']}', node_id='{field['node_id']}', type='{field['settings_type']}'{field_label_part}")
        # print("-------------------------------------------------------\n")
        # # --- END DIAGNOSTIC PRINT ---

        # _type_map: A mapping from InvokeAI's internal 'settings.type' strings
        # (e.g., "integer-field-config") to corresponding Python native types
        # (e.g., `int`). This allows for Pydantic schema generation and type
        # coercion during input application.
        self._type_map: Dict[str, Type] = {
            "integer-field-config": int,
            "float-field-config": float,
            "string-field-config": str,
            "boolean-field-config": bool,
            "image-field-config": str,
            "image-collection-field-config": list,
            "collection-field-config": list,
            "board-field-config": dict,
            "model-field-config": dict,
            "object-field-config": dict,
            # Extend this map as more InvokeAI field types are encountered.
        }

        # _field_lookup_map for flexible input resolution
        # This map will store normalized user input keys (from field_name or field_label)
        # and point to a list of *indices* into self._ordered_exposed_fields.
        # This allows us to handle duplicate field names/labels and resolve them
        # based on the order they appear in the workflow's form definition.
        self._field_lookup_map: Dict[str, List[int]] = self._build_field_lookup_map()


    def _normalize_name(self, name: str) -> str:
        """Normalizes a name for case-insensitive and space-to-underscore matching."""
        return name.lower().replace(" ", "_")


    def _build_field_lookup_map(self) -> Dict[str, List[int]]: # Changed return type
        """
        Builds a lookup map to resolve user-provided field keys (normalized field_name or field_label)
        to a list of indices into self._ordered_exposed_fields, preserving order.
        """
        lookup_map: Dict[str, List[int]] = {}
        for idx, field_info in enumerate(self._ordered_exposed_fields):
            # Store original field_name_in_node
            field_name_in_node = field_info["field_name_in_node"]
            if field_name_in_node not in lookup_map:
                lookup_map[field_name_in_node] = []
            lookup_map[field_name_in_node].append(idx) # Store index directly

            # Store normalized field_label, if present
            field_label = field_info["field_label"]
            if field_label:
                normalized_label = self._normalize_name(field_label)
                if normalized_label not in lookup_map:
                    lookup_map[normalized_label] = []
                lookup_map[normalized_label].append(idx) # Store index directly
        return lookup_map


    def _build_ordered_exposed_fields_list(self) -> List[Dict[str, Any]]:
        """
        Parses the 'form' section of the workflow JSON to create an
        ordered internal representation of all user-facing fields.

        This method correctly navigates the 'form' structure:
        - It first identifies the `rootElementId` to find the main container.
        - It then uses the `children` list within that container to determine
          the explicit order of elements.
        - For each element ID in the `children` list, it fetches the full
          element definition from the `elements` dictionary and processes
          only those of `type: "node-field"`.
        - It correctly extracts the `node_id`, `fieldName`, `settings.type`,
          and the associated *field's* `label` (if present) from the
          `batch.workflow.nodes[node_id].data.inputs[fieldName].label`, ensuring
          the ordering matches the form's `children` list.

        Returns:
            A list of dictionaries, where each dictionary contains the parsed
            information for one exposed field, in the order specified by the workflow.
            Each dictionary will include:
            - `node_id`: The ID of the node the field belongs to.
            - `field_name_in_node`: The original field name (e.g., "value", "prompt").
            - `settings_type`: The InvokeAI type (e.g., "integer-field-config").
            - `form_element_id`: The ID of the element in the 'form.elements' dict.
            - `field_label`: The user-facing label of the field (e.g., "Width", "New Seed Alpha"), or None if not found.

        Raises:
            ValueError: If critical parts of the 'form' structure (e.g., 'elements',
                        'rootElementId', or the identified container's 'children')
                        are missing or malformed, or if a 'node-field' entry itself
                        is missing essential identifiers and its type cannot be inferred.
        """
        workflow_form = self._workflow_payload.get("batch", {}).get("workflow", {}).get("form")
        
        if not isinstance(workflow_form, dict):
            raise ValueError(
                "Workflow payload does not contain a valid 'batch.workflow.form' section. "
                "Expected a dictionary for 'form'."
            )
        
        form_elements = workflow_form.get("elements")
        root_element_id = workflow_form.get("rootElementId")

        if not isinstance(form_elements, dict) or not root_element_id:
            raise ValueError(
                "Malformed 'batch.workflow.form'. Expected 'elements' dictionary "
                "and 'rootElementId' string."
            )

        root_container = form_elements.get(root_element_id)
        if not isinstance(root_container, dict) or root_container.get("type") != "container":
            raise ValueError(
                f"Root element '{root_element_id}' not found or is not a 'container' type."
            )

        # The 'children' list within the container's 'data' determines the explicit order of elements
        ordered_element_ids = root_container.get("data", {}).get("children")
        if not isinstance(ordered_element_ids, list):
            raise ValueError(
                f"Container '{root_element_id}' is malformed. Expected 'data.children' as a list of element IDs."
            )

        # Create a quick lookup for node's input field labels from 'workflow.nodes'
        # This map will store: {node_id: {field_name: field_label}}
        node_input_field_labels: Dict[str, Dict[str, str]] = {}
        workflow_nodes_list = self._workflow_payload.get("batch", {}).get("workflow", {}).get("nodes", [])
        if not workflow_nodes_list:
            warning("Warning: 'batch.workflow.nodes' section is missing or empty. Field labels will not be available.")
        
        for node in workflow_nodes_list: # Iterate through the list of workflow nodes
            if isinstance(node, dict) and "id" in node and "data" in node and isinstance(node["data"], dict):
                node_id = node["id"]
                node_input_field_labels[node_id] = {} # Initialize for this node
                node_data_inputs = node["data"].get("inputs", {})
                if isinstance(node_data_inputs, dict):
                    for field_name, field_def in node_data_inputs.items():
                        if isinstance(field_def, dict) and "label" in field_def:
                            node_input_field_labels[node_id][field_name] = field_def["label"]
        
        # Get a reference to the graph nodes for type inference
        graph_nodes = self._workflow_payload.get("batch", {}).get("graph", {}).get("nodes", {})

        # Set a new graph id (UUIDv4):
        graph_obj = self._workflow_payload.get("batch", {}).get("graph", {})
        graph_obj['id'] = str(uuid.uuid4())

        ordered_list = []
        for element_id in ordered_element_ids:
            form_element = form_elements.get(element_id)
            if not isinstance(form_element, dict):
                warning(f"Warning: Skipping malformed form element with ID '{element_id}' from children list.")
                continue

            # We are interested in elements of type "node-field" as these represent adjustable parameters.
            if form_element.get("type") == "node-field":
                field_data = form_element.get("data", {})
                field_identifier = field_data.get("fieldIdentifier", {})
                
                node_id = field_identifier.get("nodeId")
                field_name_in_node = field_identifier.get("fieldName") # This is the simplified name, e.g., "value", "prompt"
                
                # Retrieve the specific settings.type for the field.
                # If 'settings' or 'type' is missing, attempt to infer.
                settings_type = field_data.get("settings", {}).get("type")
                if not settings_type:
                    # Attempt to infer type by looking up the value in the graph node
                    if node_id and field_name_in_node and node_id in graph_nodes:
                        graph_node = graph_nodes[node_id]
                        if field_name_in_node in graph_node:
                            inferred_value = graph_node[field_name_in_node]
                            if isinstance(inferred_value, bool):
                                settings_type = "boolean-field-config"
                            elif isinstance(inferred_value, int):
                                settings_type = "integer-field-config"
                            elif isinstance(inferred_value, float):
                                settings_type = "float-field-config"
                            elif isinstance(inferred_value, str):
                                settings_type = "string-field-config"
                            elif isinstance(inferred_value, list):
                                if (
                                    (0 < len(inferred_value)) and
                                    isinstance(inferred_value[0], dict) and
                                    ('image_name' in inferred_value[0])
                                ):
                                    settings_type = "image-collection-field-config"
                                else:
                                    settings_type = "collection-field-config"
                            elif isinstance(inferred_value, dict):
                                if 'image_name' in inferred_value:
                                    settings_type = "image-field-config"
                                elif 'board_id' in inferred_value:
                                    settings_type = "board-field-config"
                                elif 'hash' in inferred_value:
                                    settings_type = "model-field-config"
                                else:
                                    raise ValueError(f"unrecognized dict element type ({field_name_in_node}): {inferred_value}")
                            elif inferred_value is None:
                                # If the value is None, we might default to string or raise an error.
                                # For now, let's default to string if no other type can be determined.
                                settings_type = "string-field-config"
                            # else: type remains None if not explicitly handled

                    if not settings_type: # If inference from graph failed or was not applicable
                        if (field_name_in_node.lower() == "board"):
                            settings_type = "board-field-config"
                        elif (field_name_in_node.lower() == "refiner_model"):
                            settings_type = "model-field-config"
                        else:
                            settings_type = "object-field-config"
                            warning(f"Malformed 'node-field' element with ID '{element_id}'. "
                                    f"Missing 'settings.type' and cannot infer type for field '{field_name_in_node}'.")
                                
                        # raise ValueError(
                        #     f"Malformed 'node-field' element with ID '{element_id}'. "
                        #     f"Missing 'settings.type' and cannot infer type for field '{field_name_in_node}'. "
                        #     f"Instance type: {type(inferred_value).__name__}. Please check workflow definition."
                        # )

                # Get the field's label from our pre-built map
                field_label = None
                if node_id in node_input_field_labels and field_name_in_node in node_input_field_labels[node_id]:
                    field_label = node_input_field_labels[node_id][field_name_in_node]
                # If field_label is an empty string, set it to None for cleaner output
                if field_label == "":
                    field_label = None
                
                # Final validation before adding to the list.
                if not all([node_id, field_name_in_node, settings_type]):
                    raise ValueError(
                        f"Malformed 'node-field' element with ID '{element_id}'. "
                        f"Missing critical data ('nodeId', 'fieldName', or inferred settings_type). "
                        f"Parsed data: {form_element}"
                    )
                
                ordered_list.append({
                    "node_id": node_id,
                    "field_name_in_node": field_name_in_node,
                    "settings_type": settings_type,
                    "form_element_id": element_id,
                    "field_label": field_label # Store the extracted field-specific label (can be None)
                })
        return ordered_list

    def get_input_schema(self) -> Type[BaseModel]:
        """
        Dynamically generates and returns a Pydantic `BaseModel` that represents
        the expected structure for user input.

        This schema is designed to accept a list of simplified field updates
        (`List[Dict[str, Any]]`). To make the schema informative, a detailed
        description is added to the 'updates' field, listing all available
        simplified field names and their corresponding InvokeAI types as
        discovered from the workflow's 'form' section. It now includes
        the *field's* label when present for enhanced clarity.

        Returns:
            A Pydantic `BaseModel` class (named `WorkflowInput`) that can be used
            to validate incoming user data.
        """
        # Build a comprehensive description for the 'updates' field
        schema_description_lines = [
            "A list of updates, where each item is a dictionary containing a single key-value pair.",
            "The key is the field identifier, which can be the `field_name_in_node` (e.g., 'value', 'prompt') "
            "or the `field_label` (e.g., 'Num Steps', 'Main Prompt').",
            "When using `field_label`, it is case-insensitive, and spaces can be replaced with underscores.",
            "The order of updates is crucial for fields with duplicate names/labels, "
            "as it determines which instance is targeted, matching their order in the workflow's form definition.",
            "\nAvailable fields in this workflow (Field Name in Node: InvokeAI Type [Field Label if present]):"
        ]
        for field_info in self._ordered_exposed_fields:
            field_name = field_info["field_name_in_node"]
            field_type = field_info["settings_type"]
            field_label = field_info["field_label"] # Retrieve the stored field-specific label

            # Format the output to include the label only if it exists and is not empty
            if field_label:
                schema_description_lines.append(f"- {field_name}: {field_type} (Label: '{field_label}')")
            else:
                schema_description_lines.append(f"- {field_name}: {field_type}")

        full_description = "\n".join(schema_description_lines)

        class WorkflowInput(BaseModel):
            """
            This schema defines the expected structure of input for updating
            InvokeAI workflow parameters.
            """
            updates: List[Dict[str, Any]] = Field(
                ...,
                description=full_description
            )
        return WorkflowInput

    def apply_inputs(self, inputs: BaseModel) -> Dict[str, Any]:
        """
        Applies validated user inputs to the workflow's graph nodes AND
        the workflow's node definitions, modifying the payload in place (on a copy).

        This method iterates through the user's provided list of updates. For each
        update, it determines the target `node_id` and `fieldName_in_node` based
        on the simplified `fieldName` and its sequential occurrence in the input list,
        relative to the ordered list of exposed fields parsed from the 'form' section.

        Args:
            inputs: An instance of the dynamically generated `WorkflowInput` model,
                    containing the user's validated input values as a list of updates.

        Returns:
            A deep copy of the original workflow JSON payload with the specified
            fields updated, ready for submission to the InvokeAI backend.

        Raises:
            ValueError: If an input item is malformed (not a single key-value dict),
                        if a target field cannot be found in the workflow (due to
                        mismatched order or non-existent field), or if the workflow
                        graph structure is invalid.
            TypeError: If a provided value cannot be coerced to the expected Python
                       type for the target InvokeAI field.
        """
        # Create a deep copy to ensure the original workflow payload remains
        # unmodified. This is crucial for idempotent operations or re-use.
        modified_payload = json.loads(json.dumps(self._workflow_payload)) 
        
        # Get references to the two sections we need to update
        graph_nodes = modified_payload.get("batch", {}).get("graph", {}).get("nodes", {})
        
        workflow_nodes_list = modified_payload.get("batch", {}).get("workflow", {}).get("nodes", [])

        # Critical validation: Ensure both graph and workflow nodes exist.
        if not graph_nodes:
            raise ValueError(
                "Workflow payload does not contain a valid 'batch.graph.nodes' section. "
                "Cannot apply inputs to a malformed workflow graph."
            )
        if not workflow_nodes_list:
            # While not strictly critical for 'graph' update, it is if user wants to sync both...
            warning("Warning: 'batch.workflow.nodes' section is missing or empty. Updates will only be applied to 'batch.graph.nodes'.")

        # Build a quick lookup map for workflow_nodes_list for efficient access
        workflow_nodes_map: Dict[str, Dict[str, Any]] = {node["id"]: node for node in workflow_nodes_list if isinstance(node, dict) and "id" in node}

        # Set to keep track of the original_order_index of fields that have been updated.
        # This allows handling of duplicate field names/labels across different nodes.
        used_field_indices: Set[int] = set()

        # Iterate through each simplified update item provided by the user.
        for update_index, update_item_dict in enumerate(inputs.updates):
            # Input validation: Ensure each item is a dictionary with exactly one key-value pair.
            if not isinstance(update_item_dict, dict) or len(update_item_dict) != 1:
                raise ValueError(
                    f"Input update item at index {update_index} is malformed. "
                    f"Expected a dictionary with a single key-value pair "
                    f"(e.g., {{'field_name_or_label': value}}), but got: {update_item_dict}"
                )

            # Extract the single key (user-provided identifier) and its value.
            user_input_key = next(iter(update_item_dict))
            value = update_item_dict[user_input_key]

            # Resolve the user_input_key to its canonical field information (list of original_order_indices).
            potential_target_indices: Optional[List[int]] = self._field_lookup_map.get(user_input_key)

            # If no direct match, try normalized label match.
            if not potential_target_indices:
                normalized_user_input_key = self._normalize_name(user_input_key)
                potential_target_indices = self._field_lookup_map.get(normalized_user_input_key)

            if not potential_target_indices:
                raise ValueError(
                    f"Input error: Field identifier '{user_input_key}' at update index {update_index} "
                    f"is not recognized as an exposed field name or label in the workflow. "
                    f"Please check the identifier and ensure it is valid for this workflow."
                )

            # Find the first available (not yet used) target index from the potential_target_indices
            found_target_original_index: Optional[int] = None
            for idx in potential_target_indices:
                if idx not in used_field_indices:
                    found_target_original_index = idx
                    break

            if found_target_original_index is None:
                raise ValueError(
                    f"Input error: Too many updates provided for field identifier '{user_input_key}'. "
                    f"All {len(potential_target_indices)} instances of this field "
                    f"(by name or label) have already been assigned a value. "
                    f"Update at index {update_index} cannot be resolved to an unused field."
                )

            # Mark this field as used so it won't be targeted again by subsequent updates
            used_field_indices.add(found_target_original_index)

            # Retrieve the full field info using the found index from the _ordered_exposed_fields
            target_field_info = self._ordered_exposed_fields[found_target_original_index]
            node_id = target_field_info["node_id"]
            field_name_in_node = target_field_info["field_name_in_node"] # The actual key for the node
            expected_type_str = target_field_info["settings_type"]
            expected_python_type = self._type_map.get(expected_type_str) # No fallback here, must be mapped

            # Critical validation: Ensure we have a mapping for the InvokeAI field type.
            if expected_python_type is None:
                raise TypeError(
                    f"Unsupported InvokeAI field config type '{expected_type_str}' for "
                    f"field '{field_name_in_node}' (Node ID: {node_id}). "
                    f"Please extend '_type_map' in WorkflowProcessor to handle this type."
                )

            # Type Coercion and Validation: Attempt to convert the input value
            # to the expected Python type. This prevents type-related errors
            # when modifying the workflow JSON.
            try:
                if value is not None and not isinstance(value, expected_python_type):
                    # Attempt explicit type conversion. Pydantic often handles this,
                    # but explicit casting ensures robust behavior here.
                    value = expected_python_type(value)
            except (ValueError, TypeError) as e:
                # Raise TypeError if the value cannot be converted, indicating invalid data.
                raise TypeError(
                    f"Type mismatch for field '{user_input_key}' (Node ID: {node_id}, "
                    f"Internal Field Name: '{field_name_in_node}'). "
                    f"Value '{value}' (type: {type(value).__name__}) could not be "
                    f"coerced to expected type '{expected_python_type.__name__}'. Error: {e}"
                )

            # Special handling for some field types (possibly need to extend?)
            if expected_type_str == "image-field-config":
                # Assuming 'value' here is the image name string provided by the user
                value_for_payload = {"image_name": value}
            elif expected_type_str == "image-collection-field-config":
                info(f'handling image collection from: {value}')
                value_for_payload = [{"image_name": v} for v in value]
            elif expected_type_str == "board-field-config":
                value_for_payload = {"board_id": value['board_id']}
            else:
                value_for_payload = value # Use the coerced value directly
            
            # Apply the update to the graph node
            if node_id in graph_nodes:
                if field_name_in_node in graph_nodes[node_id]:
                    graph_nodes[node_id][field_name_in_node] = value_for_payload
                elif field_name_in_node == "board":
                    # Board wouldn't be present if the payload field was set on "Auto"
                    # So, we have to add the key manually:
                    graph_nodes[node_id]['board'] = value_for_payload

                else:
                    warning(f"Warning: Field '{field_name_in_node}' not found in graph node '{node_id}'. Skipping update for graph.")
            else:
                warning(f"Warning: Graph node '{node_id}' not found. Skipping update for graph.")

            # Apply the update to the workflow node's inputs.value if it exists
            # This is crucial for syncing the workflow definition with the graph changes.
            workflow_node = workflow_nodes_map.get(node_id)
            if workflow_node and "data" in workflow_node and "inputs" in workflow_node["data"]:
                workflow_inputs = workflow_node["data"]["inputs"]
                if field_name_in_node in workflow_inputs and "value" in workflow_inputs[field_name_in_node]:
                    workflow_inputs[field_name_in_node]["value"] = value_for_payload
                else:
                    warning(f"Warning: Field '{field_name_in_node}' or its 'value' not found in workflow node '{node_id}' inputs. Skipping update for workflow definition.")
            else:
                warning(f"Warning: Workflow node '{node_id}' or its 'data'/'inputs' not found. Skipping update for workflow definition.")

        return modified_payload


# Define the custom output for the node (even if it's just a confirmation)
@invocation_output("EnqueueWorkflowBatchOutput")
class EnqueueWorkflowBatchOutput(BaseInvocationOutput):
    """Output for the Enqueue Workflow Batch node."""
    status: str = OutputField(description="Status of the enqueue operation (e.g., 'Success', 'Failed')")
    message: str = OutputField(description="A descriptive message about the enqueue operation.")


@invocation(
    "enqueue_workflow_batch",
    title="Enqueue Workflow Batch",
    tags=["batch", "workflow", "automation", "api"],
    category="system",
    version="1.0.0",
)
class EnqueueWorkflowBatchInvocation(BaseInvocation):
    """
    Enqueues a workflow batch by applying user updates to a pre-defined payload
    and sending it directly to the InvokeAI backend API using http.client.
    """

    # --- Node Inputs ---
    workflow_payload_filename: str = InputField(
        description="The filename of the enqueue_batch JSON payload (e.g., 'my_workflow_payload.json') "
                    "located in the node's 'workflow_payloads' subdirectory.",
        ui_order=1,
    )
    field_list_updates: str = InputField(
        description="A JSON string containing updates for the workflow's exposed fields. "
                    "Keys can be field_name_in_node (e.g., 'value', 'prompt') or field_label "
                    "(e.g., 'Num Steps', 'Main Prompt'). Field labels are case-insensitive and "
                    "support spaces as underscores (e.g., 'num_steps', 'Num_Steps', 'Num Steps'). "
                    "Example: [{'value': 100}, {'Num Steps': 25}]. "
                    "Use empty string '[]' or '{}' for no updates (will be parsed as empty list).",
        ui_component=UIComponent.Textarea,
        ui_order=2,
    )

    # --- Input Validators ---
    @validator("workflow_payload_filename")
    def validate_payload_file_exists(cls, v):
        """
        Validator to check if the specified workflow payload file exists
        in the 'workflow_payloads' subdirectory.
        """
        # __file__ refers to the current module. cls.__module__ can be used
        # to find the path in a more general way if the class is part of a package.
        # For a direct file, Path(__file__).parent is reliable.
        node_dir = Path(__file__).parent
        payloads_dir = node_dir / "workflow_payloads"
        payload_file_path = payloads_dir / v

        if not payload_file_path.is_file():
            # Raise ValueError for Pydantic validation failures
            raise ValueError(f"Workflow payload file '{v}' not found at '{payload_file_path}'.")
        return v

    @validator("field_list_updates")
    def validate_field_list_updates_format(cls, v):
        """
        Validator to check if the field_list_updates is a valid JSON string.
        Allows empty string to be valid (parsed as an empty dictionary or list).
        """
        if not v.strip(): # Treat empty string as valid JSON (empty list or dict)
            return "[]" # It expects a list of dicts for updates
        try:
            parsed_json = json.loads(v)
            if not isinstance(parsed_json, list):
                raise ValueError("Expected a JSON array (list) for 'field_list_updates'.")
            for item in parsed_json:
                if not isinstance(item, dict):
                    raise ValueError("Each item in 'field_list_updates' list must be a JSON object (dictionary).")
                if len(item) != 1:
                    raise ValueError("Each item in 'field_list_updates' list must contain exactly one key-value pair.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for field_list_updates: {e}")
        return v


    # --- Node Execution Logic ---
    def invoke(self, context: InvocationContext) -> EnqueueWorkflowBatchOutput:
        # The file existence check is now handled by the @validator.
        # We can directly construct the path here, knowing it exists.
        node_dir = Path(__file__).parent
        payloads_dir = node_dir / "workflow_payloads"
        payload_file_path = payloads_dir / self.workflow_payload_filename

        info(f"Attempting to load workflow payload from: {payload_file_path}")

        try:
            # 1. Initialize WorkflowProcessor with the selected payload
            # This can raise FileNotFoundError or ValueError (from JSONDecodeError in __init__)
            with open(payload_file_path, 'r') as inf:
                payload_json = json.load(inf)
            
            processor = WorkflowProcessor(payload_json)

            # 2. Parse and Validate the field_list_updates
            # The JSON format validation is handled by the @validator, so json.loads won't fail here for format.
            # It also ensures it's a list of single-key dicts.
            user_updates_list = json.loads(self.field_list_updates) 

            # Dynamically create schema for validation
            WorkflowInputSchema = processor.get_input_schema()

            # The WorkflowInputSchema expects a 'updates' key which is a list.
            # So, we need to pass a dictionary with 'updates' as the key.
            validated_inputs = WorkflowInputSchema(updates=user_updates_list)
            info("User inputs validated successfully against dynamic schema.")


            # 3. Apply updates to the payload
            # This can raise ValueError (e.g., due to an inconsistent workflow structure,
            # though this should ideally be caught during workflow creation/testing).
            final_payload = processor.apply_inputs(validated_inputs)
            info("Inputs applied to workflow payload successfully.")

            # ## DIAGNOSTIC SAVE #######################
            # # Save the final payload to a file for inspection
            # with open("payload.json", 'w') as outf:
            #     outf.write(json.dumps(final_payload, indent=2));
            # ## END DIAGNOSTIC ########################

            # print(f"\r\n\r\n----------------------\r\n\r\n{json.dumps(final_payload, indent=2)}\r\n\r\n------------------------\r\n\r\n")

            # 4. Prepare and send the POST request using http.client
            conn = http.client.HTTPConnection(API_HOST, API_PORT, timeout=30) # 30-second timeout

            # Encode the JSON payload to bytes
            json_body = json.dumps(final_payload).encode('utf-8')

            # Construct headers as per user's provided example
            # Note: Content-Length will be added automatically by http.client for POST requests with a body
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd", # Request compressed content
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Content-Type": "application/json", # Crucial for JSON body
                "Host": f"{API_HOST}:{API_PORT}", # As confirmed by user, include port here
                "Origin": f"http://localhost:{API_PORT}", # Origin of the request (can be UI or custom node)
                "Referer": f"http://localhost:{API_PORT}/", # Referer of the request (can be UI or custom node)
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "InvokeAI-WorkflowProcessorNode/1.0 (http.client)", # Custom user agent for clarity
                # Browser-specific headers like sec-ch-ua are generally not needed for API calls from backend
            }

            info(f"Sending POST request to http://{API_HOST}:{API_PORT}{API_PATH}")
            try:
                conn.request("POST", API_PATH, body=json_body, headers=headers)
                response = conn.getresponse()

                # --- Handle Content-Encoding (gzip, deflate) ---
                response_bytes = response.read()
                content_encoding = response.getheader('Content-Encoding')
                
                response_body_decoded = "" # Initialize here

                if content_encoding == 'gzip':
                    info("Decompressing gzipped response.")
                    response_body_decoded = gzip.decompress(response_bytes).decode('utf-8')
                elif content_encoding == 'deflate':
                    info("Decompressing deflated response.")
                    response_body_decoded = zlib.decompress(response_bytes).decode('utf-8')
                else:
                    response_body_decoded = response_bytes.decode('utf-8')

                status_code = response.status
                
                info(f"API Response - Status Code: {status_code}")
                # info(f"API Response - Body: {response_body_decoded}")

                if 200 <= status_code < 300: # Success range
                    try:
                        response_json = json.loads(response_body_decoded)
                        message = response_json.get("message", "Batch enqueued successfully!")
                    except json.JSONDecodeError:
                        message = "Batch enqueued, but response was not valid JSON. Response body might be empty or malformed."
                    return EnqueueWorkflowBatchOutput(status="Success", message=message)
                else:
                    # For non-2xx API responses, raise a RuntimeError
                    error_message = f"API returned status {status_code}: {response_body_decoded}"
                    error(error_message)
                    raise RuntimeError(f"InvokeAI API call failed: {error_message}")

            finally:
                conn.close() # Always close the connection


        # --- Centralized Exception Handling for Workflow Stopping ---
        # These exceptions indicate invalid input or critical processing failures
        # that should stop the workflow.
        except (FileNotFoundError, ValueError) as e:
            # FileNotFoundError: payload file not found (though largely caught by validator)
            # ValueError: Invalid JSON in payload, or a processing error in WorkflowProcessor
            error(f"Workflow processing error: {e}", exc_info=True)
            raise ValueError(f"Workflow input or payload error: {e}") # Re-raise as ValueError

        except ValidationError as e:
            # This catches validation errors from the dynamically generated WorkflowInputSchema
            error(f"Input validation failed: {e.errors()}", exc_info=True)
            raise ValueError(f"Invalid updates provided: {e.errors()}") # Re-raise as ValueError for clarity

        except ConnectionRefusedError:
            # Specific network error for connection issues
            error(f"Connection to InvokeAI API refused. Is the InvokeAI backend running on {API_HOST}:{API_PORT}?", exc_info=True)
            raise ConnectionRefusedError(f"Connection refused to InvokeAI API at {API_HOST}:{API_PORT}. Is it running?")

        except http.client.HTTPException as e:
            # General HTTP client errors during the request sending
            error(f"HTTP Client error during API call: {e}", exc_info=True)
            raise http.client.HTTPException(f"HTTP Client error during API call: {e}")

        except Exception as e:
            # Catch any other unexpected exceptions and wrap them as a RuntimeError
            error(f"An unhandled critical error occurred in Enqueue Workflow Batch node: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected critical error occurred: {e}")
