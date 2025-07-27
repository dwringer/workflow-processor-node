import json
from invokeai.invocation_api import (
    BaseInvocation,
    FloatOutput,
    ImageField,
    InputField,
    InvocationContext,
    IntegerOutput,
    StringOutput,
    UIComponent,
    invocation,
)
from invokeai.backend.util.logging import warning, error


class FieldListBuilderInvocation(BaseInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    existing_json: str | None = InputField(
        default=None,
        description="Optional: An existing JSON string representing a list of key-value pairs. If provided, the new entry will be appended.",
        ui_order=2,
    )
    field_name: str = InputField(
        description="The name of the field (key) for the new entry.",
        ui_order=0,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        current_list = []

        if self.existing_json and self.existing_json.strip():
            try:
                parsed_json = json.loads(self.existing_json)
                if isinstance(parsed_json, list):
                    current_list = parsed_json
                else:
                    # Handle cases where the input JSON isn't a list
                    warning("Existing JSON input was not a list. Starting a new list.")
            except json.JSONDecodeError:
                error(f"Failed to decode existing_json: {self.existing_json}. Starting a new list.")
                # If decoding fails, we start with an empty list as a fallback

        if hasattr(self, 'value'):
            input_field_value = self.value
        else:
            input_field_value = self.collection
        new_entry = {self.field_name: input_field_value}
        current_list.append(new_entry)

        output_json_string = json.dumps(current_list)  # , indent=2) # indent for readability

        return StringOutput(value=output_json_string)


@invocation(
    "field_list_builder_string",
    title="Field List Builder - String",
    tags=["json", "field", "workflow", "list", "utility", "string"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderStringInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    value: str = InputField(
        description="The value for the new entry.",
        ui_component=UIComponent.Textarea,
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_string_collection",
    title="Field List Builder - String Collection",
    tags=["json", "field", "workflow", "list", "utility", "string", "collection"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderStringCollectionInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    collection: list[str] = InputField(
        description="The collection for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_image",
    title="Field List Builder - Image",
    tags=["json", "field", "workflow", "list", "utility", "image"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderImageInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    value: ImageField = InputField(
        description="The value for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        current_list = []

        if self.existing_json and self.existing_json.strip():
            try:
                parsed_json = json.loads(self.existing_json)
                if isinstance(parsed_json, list):
                    current_list = parsed_json
                else:
                    # Handle cases where the input JSON isn't a list
                    warning("Existing JSON input was not a list. Starting a new list.")
            except json.JSONDecodeError:
                error(f"Failed to decode existing_json: {self.existing_json}. Starting a new list.")
                # If decoding fails, we start with an empty list as a fallback

        new_entry = {self.field_name: self.value.image_name}
        current_list.append(new_entry)

        output_json_string = json.dumps(current_list)  # , indent=2) # indent for readability

        return_value = StringOutput(value=output_json_string)
        return return_value


@invocation(
    "field_list_builder_image_collection",
    title="Field List Builder - Image Collection",
    tags=["json", "field", "workflow", "list", "utility", "image", "collection"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderImageCollectionInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    collection: list[ImageField] = InputField(
        description="The image collection for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        current_list = []

        if self.existing_json and self.existing_json.strip():
            try:
                parsed_json = json.loads(self.existing_json)
                if isinstance(parsed_json, list):
                    current_list = parsed_json
                else:
                    # Handle cases where the input JSON isn't a list
                    warning("Existing JSON input was not a list. Starting a new list.")
            except json.JSONDecodeError:
                error(f"Failed to decode existing_json: {self.existing_json}. Starting a new list.")
                # If decoding fails, we start with an empty list as a fallback

        new_entry = {self.field_name: [img_field.image_name for img_field in self.collection]}
        current_list.append(new_entry)

        output_json_string = json.dumps(current_list)  # , indent=2) # indent for readability

        return_value = StringOutput(value=output_json_string)
        return return_value


@invocation(
    "field_list_builder_integer",
    title="Field List Builder - Integer",
    tags=["json", "field", "workflow", "list", "utility", "integer"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderIntegerInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    value: int = InputField(
        description="The value for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value

    
@invocation(
    "field_list_builder_integer_collection",
    title="Field List Builder - Integer Collection",
    tags=["json", "field", "workflow", "list", "utility", "integer", "collection"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderIntegerCollectionInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    collection: list[int] = InputField(
        description="The collection for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_float",
    title="Field List Builder - Float",
    tags=["json", "field", "workflow", "list", "utility", "float"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderFloatInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    value: float = InputField(
        description="The value for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_float_collection",
    title="Field List Builder - Float Collection",
    tags=["json", "field", "workflow", "list", "utility", "float", "collection"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderFloatCollectionInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    collection: list[float] = InputField(
        description="The collection for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_boolean",
    title="Field List Builder - Boolean",
    tags=["json", "field", "workflow", "list", "utility", "boolean"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderBooleanInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    value: bool = InputField(
        description="The value for the new entry.",
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


# DISABLED
#  This is currently deactivated because
#  boolean collections are not properly
#  supported in the linear UI as of 5.9
# --------------------------------------
# @invocation(
#     "field_list_builder_boolean_collection",
#     title="Field List Builder - Boolean Collection",
#     tags=["json", "field", "workflow", "list", "utility", "boolean", "collection"],
#     category="utilities",
#     version="1.0.0"
# )
# class FieldListBuilderBooleanCollectionInvocation(FieldListBuilderInvocation):
#     """
#     Builds or appends to a JSON list containing single key-value pair dictionaries.
#     """

#     collection: list[bool] = InputField(
#         default=[],
#         description="The collection for the new entry.",
#         ui_order=1,
#     )

#     def invoke(self, context: InvocationContext) -> StringOutput:
#         return_value : StringOutput = super().invoke(context)
#         return return_value
# --------------------------------------


@invocation(
    "field_list_builder_join",
    title="Field List Builder - Join",
    tags=["json", "field", "workflow", "list", "utility", "join", "concatenate"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderJoinInvocation(BaseInvocation):
    """
    Concatenates two JSON lists.
    """

    first: str = InputField(
        description="The first JSON field list for joining.",
        ui_component=UIComponent.Textarea,
        ui_order=0,
    )
    second: str = InputField(
        description="The second JSON field list for joining.",
        ui_component=UIComponent.Textarea,
        ui_order=1,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        try:
            first_list = json.loads(self.first)
            if not isinstance(first_list, list):
                warning("First List input was not a list. Using a blank list.")
                first_list = []
        except json.JSONDecodeError:
                error(f"Failed to decode first_list: {self.first_list}. Using a blank list.")
        try:
            second_list = json.loads(self.second)
            if not isinstance(second_list, list):
                warning("Second List input was not a list. Using a blank list.")
                second_list = []
        except json.JSONDecodeError:
                error(f"Failed to decode first_list: {self.first_list}. Using a blank list.")

        output_json_obj = first_list + second_list
        
        output_json_string = json.dumps(output_json_obj)

        return_value = StringOutput(value=output_json_string)
        return return_value
