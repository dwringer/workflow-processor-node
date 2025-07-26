import copy
import gzip # Import gzip for decompression
import http.client # Using built-in http.client for HTTP requests
import json
import os
import zlib # Import zlib for deflate decompression

from pathlib import Path
from typing import Dict, Any, Type, Optional, List, Union

from pydantic import BaseModel, Field, create_model, ValidationError, validator # Import validator

from invokeai.invocation_api import (
    BaseInvocation,
    BaseInvocationOutput,
    InputField,
    InvocationContext,
    OutputField,
    StringOutput, # For potential error messages or confirmation
    invocation,
    invocation_output,
    UIComponent,
)
from invokeai.backend.util.logging import info, warning, error


# # --- Your WorkflowProcessor Class (Copied for Self-Contained) ---
# class WorkflowProcessor:
#     """
#     The WorkflowProcessor is designed to bridge the gap between a raw InvokeAI
#     workflow JSON and a user-friendly API for parameter adjustments.

#     It performs three primary functions:
#     1.  **Parsing:** Extracts relevant user-exposed input fields from the
#         complex InvokeAI workflow JSON, specifically from the 'form' section,
#         organizing them into an ordered, internally manageable structure.
#     2.  **Schema Generation:** Dynamically creates a Pydantic `BaseModel` schema
#         that defines the expected structure of user input. This schema is designed
#         to be both simple for the user to provide and informative for developers
#         to understand available fields.
#     3.  **Input Application:** Takes validated user inputs and intelligently
#         applies them to the correct fields within the workflow's graph nodes AND
#         the workflow's node definitions, preparing the payload for submission
#         to the InvokeAI backend.

#     A key design choice is to support simplified user input (e.g., `{"value": 100}`)
#     even when multiple nodes in the workflow might have fields with the same name.
#     This is achieved by relying on the *relative order* of duplicate field names
#     in the user's input list, matching them to the order defined in the workflow's
#     'form' section 'children' list.
#     """

#     # Mapping from InvokeAI field type configurations to Python types
#     _type_map: Dict[str, Type] = {
#         "integer-field-config": int,
#         "float-field-config": float,
#         "string-field-config": str,
#         "ImageField": str, # User provides image name as string, payload expects {"image_name": "..."}
#         "boolean-field-config": bool, # Added boolean
#     }

#     def __init__(self, workflow_payload_path: Path):
#         """
#         Initializes the processor by loading the base workflow payload and parsing its structure.

#         Args:
#             workflow_payload_path: The path to the base enqueue_batch JSON payload file.
#         """
#         if not workflow_payload_path.exists():
#             raise FileNotFoundError(f"Workflow payload file not found: {workflow_payload_path}")
#         try:
#             with open(workflow_payload_path, 'r', encoding='utf-8') as f:
#                 self._workflow_payload = json.load(f)
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON format in {workflow_payload_path}: {e}")

#         # Deep copy for modification
#         # It's good practice to make a copy of the base nodes for applying inputs,
#         # ensuring the original _workflow_payload object isn't altered
#         # by subsequent calls to apply_inputs if this processor instance is reused.
#         # This will be used as the starting point for `final_payload` in `apply_inputs`.
#         self._base_batch_graph_nodes = copy.deepcopy(self._workflow_payload['batch']['graph']['nodes'])
#         self._base_workflow_nodes = copy.deepcopy(self._workflow_payload['batch']['workflow']['nodes'])


#         # Build the ordered list of exposed fields for schema generation and input application
#         self._ordered_exposed_fields = self._build_ordered_exposed_fields_list()
#         info(f"--- Detected Order of Exposed Fields for {workflow_payload_path.name} ---")
#         for i, field in enumerate(self._ordered_exposed_fields):
#             info(f"  {i+1}. {field['label']} ({field['field_name']}) [node: {field['node_id']}]")

#     def _build_ordered_exposed_fields_list(self) -> List[Dict[str, Any]]:
#         """
#         Parses the workflow's 'form' section to create an ordered list of
#         user-exposed fields. This order is crucial for handling duplicate field names.
#         """
#         exposed_elements_in_order = []
#         workflow_form = self._workflow_payload.get('batch', {}).get('workflow', {}).get('form', {})
#         root_element_id = workflow_form.get('rootElementId')

#         if not root_element_id or 'elements' not in workflow_form:
#             warning("Workflow form or root element not found. No exposed fields detected.")
#             return []

#         elements_map = workflow_form['elements']

#         def recurse_for_exposed_elements(element_id: str):
#             element = elements_map.get(element_id)
#             if not element:
#                 return

#             if element.get('type') == 'node-field':
#                 exposed_elements_in_order.append(element)
#             elif element.get('type') == 'container':
#                 if 'data' in element and 'children' in element['data']:
#                     for child_id in element['data']['children']:
#                         recurse_for_exposed_elements(child_id)

#         recurse_for_exposed_elements(root_element_id)

#         # Process the raw exposed field elements to extract relevant info
#         processed_fields = []
#         for field_element in exposed_elements_in_order:
#             field_data = field_element.get('data', {})
#             field_identifier = field_data.get('fieldIdentifier', {})
#             field_settings = field_data.get('settings', {})

#             node_id = field_identifier.get('nodeId')
#             field_name = field_identifier.get('fieldName')
#             # Prefer 'label' from settings, then from data, then default to field_name
#             field_label = field_settings.get('label') or field_data.get('label') or field_name
#             field_type_config = field_settings.get('type')

#             # Determine the Pydantic type for the schema based on InvokeAI's type config
#             pydantic_type = self._type_map.get(field_type_config)
#             if not pydantic_type:
#                 # Fallback based on component type or common names if type_config is missing or unknown
#                 component_type = field_settings.get('component')
#                 if component_type == 'number-input':
#                     pydantic_type = float # Default to float for generic number inputs
#                 elif field_name in ['prompt', 'text', 'notes', 'description', 'label', 'custom_label']:
#                     pydantic_type = str
#                 elif field_name == "image":
#                     pydantic_type = str # For schema, it's a string (image_name)
#                     field_type_config = "ImageField" # Standardize internal representation
#                 elif field_name in ["true", "false", "add_noise", "expand_to_fit", "flip_horizontal", "flip_vertical", "disable", "normalize_channels", "use_gaussian_mutation", "expand_t5_embeddings", "scale_delta_output", "touch_timestamp"]:
#                     pydantic_type = bool
#                     field_type_config = "boolean-field-config" # Standardize internal representation
#                 else:
#                     warning(f"Unknown field type configuration '{field_type_config}' "
#                             f"or component '{component_type}' for field '{field_name}' in node '{node_id}'. "
#                             f"Defaulting to str for schema generation.")
#                     pydantic_type = str

#             # Ensure label is not an empty string, set to None for cleaner output
#             if field_label == "":
#                 field_label = None

#             processed_fields.append({
#                 "element_id": field_element.get('id'),
#                 "node_id": node_id,
#                 "field_name": field_name,
#                 "label": field_label,
#                 "type_config": field_type_config,
#                 "pydantic_type": pydantic_type,
#             })
#         return processed_fields

#     def get_input_schema(self) -> Type[BaseModel]:
#         """
#         Generates a Pydantic BaseModel schema based on the exposed input fields.
#         This schema is suitable for validating user API inputs.
#         """
#         fields = {}
#         descriptions = []
#         for i, field_info in enumerate(self._ordered_exposed_fields):
#             element_id = field_info['element_id']
#             field_name_in_node = field_info['field_name']
#             field_label = field_info['label'] or field_name_in_node # Fallback to field_name_in_node if label is None
#             pydantic_type = field_info['pydantic_type']

#             # Use element_id as the field name in the Pydantic schema
#             fields[element_id] = (Optional[pydantic_type], Field(
#                 default=None, # All fields are optional at this level, user provides what they want to update
#                 title=field_label,
#                 description=(f"Node ID: {field_info['node_id']}, Field Name: {field_name_in_node}, "
#                              f"InvokeAI Type: {field_info['type_config']}. "
#                              f"Original Label: '{field_info['label']}'") # Include original label for clarity
#             ))
#             descriptions.append(
#                 f"- **{field_label}** (`{element_id}`): For node `{field_info['node_id']}` field `{field_name_in_node}`. Type: `{field_info['type_config']}`."
#             )

#         schema_description = (
#             "This schema defines the expected structure of input for updating "
#             "InvokeAI workflow parameters. Provide a dictionary where keys are "
#             "the `element_id`s from the workflow's 'form' section, and values "
#             "are the desired new values for those fields.\n\n"
#             "**Available Exposed Fields (from workflow's UI form, in order):**\n"
#             f"{'    ' + os.linesep.join(descriptions)}"
#         )
#         return create_model(
#             "WorkflowInputSchema",
#             __doc__=schema_description,
#             **fields
#         )


#     def apply_inputs(self, validated_inputs_model: BaseModel) -> Dict[str, Any]:
#         """
#         Applies validated user inputs to a deep copy of the base workflow payload.

#         Args:
#             validated_inputs_model: An instance of the Pydantic schema generated by get_input_schema,
#                                     containing the validated user inputs.

#         Returns:
#             A new dictionary representing the modified enqueue_batch JSON payload.
#         """
#         modified_workflow_payload = copy.deepcopy(self._workflow_payload)

#         # Get references to the two sections we need to update
#         graph_nodes = modified_workflow_payload.get("batch", {}).get("graph", {}).get("nodes", {})
#         # Note: workflow_nodes_list is actually a dict in the current payload structure
#         workflow_nodes_map = modified_workflow_payload.get("batch", {}).get("workflow", {}).get("nodes", {})


#         # Critical validation: Ensure both graph and workflow nodes exist.
#         if not graph_nodes:
#             raise ValueError(
#                 "Workflow payload does not contain a valid 'batch.graph.nodes' section. "
#                 "Cannot apply inputs to a malformed workflow graph."
#             )
#         if not workflow_nodes_map:
#             warning("Warning: 'batch.workflow.nodes' section is missing or empty. Updates will only be applied to 'batch.graph.nodes'.")
        
#         # Only take fields that were actually set by the user (not None defaults)
#         # The keys here are the element_ids from the form
#         user_inputs = validated_inputs_model.model_dump(exclude_unset=True)

#         # Iterate through the ordered exposed fields to apply updates
#         # This ensures correct mapping even with duplicate field names,
#         # as we are processing based on the 'form's defined order.
#         for field_info in self._ordered_exposed_fields:
#             element_id = field_info['element_id']

#             # Skip if this field was not provided in the user's input
#             if element_id not in user_inputs:
#                 continue 

#             node_id = field_info['node_id']
#             field_name_in_node = field_info['field_name']
#             expected_type_config = field_info['type_config']
            
#             value = user_inputs[element_id] # Value already validated by Pydantic schema

#             # --- Apply specific transformations for InvokeAI payload format ---
#             value_for_payload = value
#             if expected_type_config == "ImageField":
#                 # For ImageField, user provides a string (image_name), but payload needs a dict
#                 if isinstance(value, str): # Pydantic ensures it's str, just a safety check
#                     value_for_payload = {"image_name": value}
            
#             # --- Apply update to batch.graph.nodes ---
#             target_graph_node = graph_nodes.get(node_id)
#             if target_graph_node:
#                 # Prioritize direct assignment, then common nested paths based on observed payloads
#                 if field_name_in_node in target_graph_node:
#                     target_graph_node[field_name_in_node] = value_for_payload
#                 elif "inputs" in target_graph_node and field_name_in_node in target_graph_node["inputs"]:
#                     target_graph_node["inputs"][field_name_in_node] = value_for_payload
#                 elif "data" in target_graph_node and field_name_in_node in target_graph_node["data"]:
#                     target_graph_node["data"][field_name_in_node] = value_for_payload
#                 elif "data" in target_graph_node and "inputs" in target_graph_node["data"] and field_name_in_node in target_graph_node["data"]["inputs"]:
#                     target_graph_node["data"]["inputs"][field_name_in_node] = value_for_payload
#                 else:
#                     # This is the warning branch you observed. If the field isn't in common paths,
#                     # we attempt to add it directly at the top level of the node.
#                     warning(f"Field '{field_name_in_node}' not found in common paths within graph node '{node_id}' in batch.graph.nodes. Attempting direct assignment. This might indicate an implicit field or a non-standard structure. Verify generated payload.")
#                     target_graph_node[field_name_in_node] = value_for_payload
#             else:
#                 warning(f"Node '{node_id}' not found in batch.graph.nodes. Cannot apply update for '{field_name_in_node}'. This is unexpected if the workflow definition is valid.")


#             # --- Apply update to batch.workflow.nodes (for consistency/reference) ---
#             target_workflow_node = workflow_nodes_map.get(node_id)
#             if target_workflow_node:
#                 # Workflow nodes store values under data.inputs.<field_name>.value
#                 node_data_inputs = target_workflow_node.get("data", {}).get("inputs")
#                 if isinstance(node_data_inputs, dict) and field_name_in_node in node_data_inputs:
#                     field_definition = node_data_inputs[field_name_in_node]
#                     if isinstance(field_definition, dict):
#                         field_definition["value"] = value_for_payload
#                     else:
#                         warning(f"Workflow node '{node_id}' has malformed input definition for field '{field_name_in_node}'. Skipping update in workflow.nodes. This is unexpected.")
#                 else:
#                     warning(f"Field '{field_name_in_node}' not found in inputs of workflow node '{node_id}' in batch.workflow.nodes. Skipping update.")
#             # Else: Node not found in workflow_nodes_map, warning already given earlier if map was empty.

#         return modified_workflow_payload

# # --- End of WorkflowProcessor Class ---


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

        # --- DIAGNOSTIC PRINT ---
        # This will show the exact order of fields that the processor has extracted
        # from the workflow's 'form' section, including their user-facing labels.
        print("\n--- Detected Order of Exposed Fields (Internal View) ---")
        for i, field in enumerate(self._ordered_exposed_fields):
            field_label_part = f" (Label: '{field['field_label']}')" if field['field_label'] else ""
            print(f"[{i}]: field_name='{field['field_name_in_node']}', node_id='{field['node_id']}', type='{field['settings_type']}'{field_label_part}")
        print("-------------------------------------------------------\n")
        # --- END DIAGNOSTIC PRINT ---


        # _type_map: A mapping from InvokeAI's internal 'settings.type' strings
        # (e.g., "integer-field-config") to corresponding Python native types
        # (e.g., `int`). This allows for Pydantic schema generation and type
        # coercion during input application.
        self._type_map: Dict[str, Type] = {
            "integer-field-config": int,
            "float-field-config": float,
            "string-field-config": str,
            # Extend this map as more InvokeAI field types are encountered.
            # "ImageField" is a custom internal type for image data, mapped to string.
            "ImageField": str, 
        }

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

        # NEW: Create a quick lookup for node's input field labels from 'workflow.nodes'
        # This map will store: {node_id: {field_name: field_label}}
        node_input_field_labels: Dict[str, Dict[str, str]] = {}
        workflow_nodes_list = self._workflow_payload.get("batch", {}).get("workflow", {}).get("nodes", [])
        if not workflow_nodes_list:
            print("Warning: 'batch.workflow.nodes' section is missing or empty. Field labels will not be available.")
        
        for node in workflow_nodes_list: # Iterate through the list of workflow nodes
            if isinstance(node, dict) and "id" in node and "data" in node and isinstance(node["data"], dict):
                node_id = node["id"]
                node_input_field_labels[node_id] = {} # Initialize for this node
                node_data_inputs = node["data"].get("inputs", {})
                if isinstance(node_data_inputs, dict):
                    for field_name, field_def in node_data_inputs.items():
                        if isinstance(field_def, dict) and "label" in field_def:
                            node_input_field_labels[node_id][field_name] = field_def["label"]
        
        ordered_list = []
        for element_id in ordered_element_ids:
            form_element = form_elements.get(element_id)
            if not isinstance(form_element, dict):
                print(f"Warning: Skipping malformed form element with ID '{element_id}' from children list.")
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
                    # Special handling for known field names that might lack 'settings.type'
                    if field_name_in_node == "image":
                        settings_type = "ImageField" # Assign a custom internal type name for images
                    else:
                        raise ValueError(
                            f"Malformed 'node-field' element with ID '{element_id}'. "
                            f"Missing 'settings.type' and cannot infer type for field '{field_name_in_node}'."
                        )

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
            "The key is the simplified field name (e.g., 'value', 'prompt'), and the value is the new setting.",
            "The order of updates is crucial for fields with duplicate names (e.g., two 'value' fields) "
            "as it determines which instance is targeted, matching their order in the workflow's form definition.",
            "\nAvailable fields in this workflow (Name: InvokeAI Type [Field Label if present]):"
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
            # While not strictly critical for 'graph' update, it is if user wants to sync both.
            print("Warning: 'batch.workflow.nodes' section is missing or empty. Updates will only be applied to 'batch.graph.nodes'.")
        
        # NEW: Build a quick lookup map for workflow_nodes_list for efficient access
        workflow_nodes_map: Dict[str, Dict[str, Any]] = {node["id"]: node for node in workflow_nodes_list if isinstance(node, dict) and "id" in node}

        # field_cursors: A dictionary to keep track of which occurrence of a
        # given 'simplified_field_name' (e.g., "value") we are currently
        # processing from the user's input list. This enables disambiguation
        # for duplicate field names.
        # Format: {simplified_field_name: current_index_of_occurrence (0-based)}
        field_cursors: Dict[str, int] = {}

        # Iterate through each simplified update item provided by the user.
        for update_index, update_item_dict in enumerate(inputs.updates):
            # Input validation: Ensure each item is a dictionary with exactly one key-value pair.
            if not isinstance(update_item_dict, dict) or len(update_item_dict) != 1:
                raise ValueError(
                    f"Input update item at index {update_index} is malformed. "
                    f"Expected a dictionary with a single key-value pair "
                    f"(e.g., {{'field_name': value}}), but got: {update_item_dict}"
                )

            # Extract the single key (simplified field name) and its value.
            simplified_field_name = next(iter(update_item_dict))
            value = update_item_dict[simplified_field_name]

            # Increment the cursor for this specific field name.
            # This tells us which instance of 'simplified_field_name' we are targeting.
            field_cursors[simplified_field_name] = field_cursors.get(simplified_field_name, -1) + 1
            current_cursor = field_cursors[simplified_field_name]

            # Locate the target field's metadata in our pre-built ordered list
            # (which comes from the 'form' section).
            # We search for the Nth occurrence of this simplified_field_name.
            target_field_info: Optional[Dict[str, Any]] = None
            found_count = 0
            for info in self._ordered_exposed_fields:
                if info["field_name_in_node"] == simplified_field_name:
                    if found_count == current_cursor:
                        target_field_info = info
                        break # Found the correct instance
                    found_count += 1
            
            # Critical validation: If no matching exposed field is found, it indicates
            # either a mismatch in the user's input order (too many updates for a
            # given field name) or an invalid field name not exposed in the workflow.
            if not target_field_info:
                raise ValueError(
                    f"Input error: Could not find the {current_cursor + 1}th occurrence of "
                    f"exposed field '{simplified_field_name}' in the workflow definition. "
                    f"Please check the field name and its relative order in the input list, "
                    f"or if it is an exposed field at all."
                )

            node_id = target_field_info["node_id"]
            field_name_in_node = target_field_info["field_name_in_node"] # The actual key for the node
            expected_type_str = target_field_info["settings_type"]
            expected_python_type = self._type_map.get(expected_type_str) # No fallback here, must be mapped

            # Critical validation: Ensure we have a mapping for the InvokeAI field type.
            if expected_python_type is None:
                raise TypeError(
                    f"Unsupported InvokeAI field config type '{expected_type_str}' for "
                    f"field '{simplified_field_name}' (Node ID: {node_id}). "
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
                    f"Type mismatch for field '{simplified_field_name}' (Node ID: {node_id}). "
                    f"Value '{value}' (type: {type(value).__name__}) could not be converted "
                    f"to expected type '{expected_python_type.__name__}'. Original error: {e}"
                )

            # Special handling for ImageField type (might we need to add bool or other types here?)
            if expected_type_str == "ImageField":
                # Assuming 'value' here is the image name string provided by the user
                value_for_payload = {"image_name": value}
            else:
                value_for_payload = value # Use the coerced value directly
            
            # --- Apply update to batch.graph.nodes ---
            target_graph_node = graph_nodes.get(node_id)
            if not target_graph_node:
                # This indicates a severe inconsistency between exposed_fields (from 'form')
                # and the actual graph nodes, which is a critical internal workflow error.
                raise ValueError(
                    f"Internal workflow error: Node ID '{node_id}' for exposed field "
                    f"'{simplified_field_name}' not found in 'batch.graph.nodes'. "
                    f"The workflow definition may be corrupted or inconsistent."
                )

            # Logic to find and update the field in the graph node
            if field_name_in_node in target_graph_node:
                target_graph_node[field_name_in_node] = value_for_payload
            elif "inputs" in target_graph_node and field_name_in_node in target_graph_node["inputs"]:
                target_graph_node["inputs"][field_name_in_node] = value_for_payload
            elif "data" in target_graph_node and field_name_in_node in target_graph_node["data"]:
                target_graph_node["data"][field_name_in_node] = value_for_payload
            elif "data" in target_graph_node and "inputs" in target_graph_node["data"] and field_name_in_node in target_graph_node["data"]["inputs"]:
                target_graph_node["data"]["inputs"][field_name_in_node] = value_for_payload
            else:
                print(f"Warning: Field '{field_name_in_node}' not found in common paths within graph node '{node_id}'. Attempting direct assignment. "
                      f"Review workflow structure if this message persists for a valid workflow.")
                target_graph_node[field_name_in_node] = value_for_payload

            # --- Apply update to batch.workflow.nodes ---
            # Locate the node in the workflow_nodes_list using the map for efficiency
            target_workflow_node = workflow_nodes_map.get(node_id)
            if target_workflow_node:
                # The value needs to be set in data.inputs.<field_name>.value
                node_data_inputs = target_workflow_node.get("data", {}).get("inputs")
                if isinstance(node_data_inputs, dict) and field_name_in_node in node_data_inputs:
                    field_definition = node_data_inputs[field_name_in_node]
                    if isinstance(field_definition, dict):
                        field_definition["value"] = value_for_payload
                    else:
                        print(f"Warning: Workflow node '{node_id}' has malformed input definition for field '{field_name_in_node}'. Skipping update in workflow.nodes.")
                else:
                    print(f"Warning: Field '{field_name_in_node}' not found in inputs of workflow node '{node_id}'. Skipping update in workflow.nodes.")
            else:
                # This should ideally not happen if _build_ordered_exposed_fields_list is accurate,
                # as it builds from workflow.nodes. However, defensive check is good.
                print(f"Warning: Workflow node ID '{node_id}' for exposed field '{simplified_field_name}' not found in 'batch.workflow.nodes'. Skipping update in workflow.nodes.")

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
    Enqueues a workflow batch by applying user updates to a pre-defined template
    and sending it directly to the InvokeAI backend API using http.client.
    """

    # --- Node Inputs ---
    workflow_template_filename: str = InputField(
        description="The filename of the enqueue_batch JSON template (e.g., 'my_workflow_template.json') "
                    "located in the node's 'workflow_templates' subdirectory.",
        ui_order=1,
    )
    updates_json_string: str = InputField(
        description="A JSON string containing updates for the workflow's exposed fields. "
                    "Keys are element_ids (from workflow form), values are new data. "
                    "Example: {'node-field-abc': 100, 'node-field-xyz': 'my_image.png'}. "
                    "Use empty string '{}' for no updates.",
        ui_component=UIComponent.Textarea,
        ui_order=2,
    )

    # --- Input Validators ---
    @validator("workflow_template_filename")
    def validate_template_file_exists(cls, v):
        """
        Validator to check if the specified workflow template file exists
        in the 'workflow_templates' subdirectory.
        """
        # __file__ refers to the current module. cls.__module__ can be used
        # to find the path in a more general way if the class is part of a package.
        # For a direct file, Path(__file__).parent is reliable.
        node_dir = Path(__file__).parent
        templates_dir = node_dir / "workflow_templates"
        template_file_path = templates_dir / v

        if not template_file_path.is_file():
            # Raise ValueError for Pydantic validation failures
            raise ValueError(f"Workflow template file '{v}' not found at '{template_file_path}'.")
        return v

    @validator("updates_json_string")
    def validate_updates_json_string_format(cls, v):
        """
        Validator to check if the updates_json_string is a valid JSON string.
        Allows empty string to be valid (parsed as an empty dictionary).
        """
        if not v.strip(): # Treat empty string as valid JSON (empty dict)
            return "{}"
        try:
            json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for updates_json_string: {e}")
        return v


    # --- Node Execution Logic ---
    def invoke(self, context: InvocationContext) -> EnqueueWorkflowBatchOutput:
        # The file existence check is now handled by the @validator.
        # We can directly construct the path here, knowing it exists.
        node_dir = Path(__file__).parent
        templates_dir = node_dir / "workflow_templates"
        template_file_path = templates_dir / self.workflow_template_filename

        info(f"Attempting to load workflow template from: {template_file_path}")

        # Define the InvokeAI API host and path
        # As confirmed by user, host is localhost:9090 for the API
        API_HOST = "localhost"
        API_PORT = 9090
        API_PATH = "/api/v1/queue/default/enqueue_batch" # This part seems standard

        try:
            # 1. Initialize WorkflowProcessor with the selected template
            # This can raise FileNotFoundError or ValueError (from JSONDecodeError in __init__)
            with open(template_file_path, 'r') as inf:
                template_json = json.load(inf)
            
            processor = WorkflowProcessor(template_json)

            # 2. Parse and Validate the updates_json_string
            # The JSON format validation is handled by the @validator, so json.loads won't fail here for format.
            user_updates_dict = json.loads(self.updates_json_string) 

            # Dynamically create schema for validation
            WorkflowInputSchema = processor.get_input_schema()

            # Validate the incoming user updates against the dynamic schema
            # Pydantic will handle coercion and raise ValidationError if types are incompatible.
            # This is where general input validation failures will occur.
            validated_inputs = WorkflowInputSchema(**user_updates_dict)
            info("User inputs validated successfully against dynamic schema.")


            # 3. Apply updates to the payload
            # This can raise ValueError (e.g., due to an inconsistent workflow structure,
            # though this should ideally be caught during workflow creation/testing).
            final_payload = processor.apply_inputs(validated_inputs)
            info("Inputs applied to workflow payload successfully.")

            print(f"\r\n\r\n----------------------\r\n\r\n{final_payload}\r\n\r\n------------------------\r\n\r\n")

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
                "Origin": "http://localhost:9090", # Origin of the request (can be UI or custom node)
                "Referer": "http://localhost:9090/", # Referer of the request (can be UI or custom node)
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "InvokeAI-CustomNode/1.0 (http.client)", # Custom user agent for clarity
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
                info(f"API Response - Body: {response_body_decoded}")

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
            # FileNotFoundError: template file not found (though largely caught by validator)
            # ValueError: Invalid JSON in template, or a processing error in WorkflowProcessor
            error(f"Workflow processing error: {e}", exc_info=True)
            raise ValueError(f"Workflow input or template error: {e}") # Re-raise as ValueError

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

