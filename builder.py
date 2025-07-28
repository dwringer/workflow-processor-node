import json
from invokeai.invocation_api import (
    SCHEDULER_NAME_VALUES,
    BaseInvocation,
    FieldDescriptions,
    FloatOutput,
    ImageField,
    Input,
    InputField,
    InvocationContext,
    IntegerOutput,
    ModelIdentifierField,
    StringOutput,
    UIComponent,
    UIType,
    WithBoard,
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
        elif hasattr(self, 'board'):
            if self.board:
                input_field_value = {'board_id': self.board.board_id}
            else:
                input_field_value = "auto"
        elif hasattr(self, 'model'):
            input_field_value = {
                'key': self.model.key,
                'hash': self.model.hash,
                'name': self.model.name,
                'base': self.model.base,
                'type': self.model.type,
                'submodel_type': self.model.submodel_type if hasattr(self.model, 'submodel_type') else None
            }
        elif hasattr(self, 'collection'):
            input_field_value = self.collection
        else:
            raise ValueError(f"Unrecognized input field value in {json.dumps(self.keys())}")
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
    "field_list_builder_board",
    title="Field List Builder - Board",
    tags=["json", "field", "workflow", "list", "utility", "board"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderBoardInvocation(FieldListBuilderInvocation, WithBoard):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
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
    "field_list_builder_controlnet",
    title="Field List Builder - ControlNet",
    tags=["json", "field", "workflow", "list", "utility", "controlnet"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderControlNetInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.controlnet_model,
        ui_order=1,
        ui_type=UIType.ControlNetModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_ip_adapter",
    title="Field List Builder - IP Adapter",
    tags=["json", "field", "workflow", "list", "utility", "ip", "adapter"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderIPAdapterInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.ip_adapter,
        ui_order=1,
        ui_type=UIType.IPAdapterModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_controllora",
    title="Field List Builder - ControlLoRA",
    tags=["json", "field", "workflow", "list", "utility", "controllora"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderControlLoRAInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.control_lora_model,
        ui_order=1,
        ui_type=UIType.ControlLoRAModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_lora",
    title="Field List Builder - LoRA",
    tags=["json", "field", "workflow", "list", "utility", "lora"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderLoRAInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.lora_model,
        ui_order=1,
        ui_type=UIType.LoRAModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value : StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_flux_main_model",
    title="Field List Builder - FLUX Main Model",
    tags=["json", "field", "workflow", "list", "utility", "flux", "main", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderFLUXMainModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a main model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.flux_model,
        ui_order=1,
        ui_type=UIType.FluxMainModel,
        input=Input.Direct,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_flux_redux_model",
    title="Field List Builder - FLUX Redux Model",
    tags=["json", "field", "workflow", "list", "utility", "flux", "redux", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderFLUXReduxModelBase(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a FLUX Redux model.
    """

    model: ModelIdentifierField = InputField(
        description="The FLUX Redux model to use.",
        title="FLUX Redux Model",
        ui_order=1,
        ui_type=UIType.FluxReduxModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_t5_model",
    title="Field List Builder - T5 Model",
    tags=["json", "field", "workflow", "list", "utility", "t5", "encoder"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderT5ModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a T5 encoder model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.t5_encoder,
        ui_order=1,
        ui_type=UIType.T5EncoderModel,
        input=Input.Direct,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_clip_model",
    title="Field List Builder - CLIP Model",
    tags=["json", "field", "workflow", "list", "utility", "clip", "encoder"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderCLIPModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP embed model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.clip_embed_model,
        ui_order=1,
        ui_type=UIType.CLIPEmbedModel,
        input=Input.Direct,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_flux_vae",
    title="Field List Builder - FLUX VAE",
    tags=["json", "field", "workflow", "list", "utility", "vae", "flux"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderFLUXVAEInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.vae_model,
        ui_order=1,
        ui_type=UIType.FluxVAEModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_sd15_main_model",
    title="Field List Builder - SD1.5 Main Model",
    tags=["json", "field", "workflow", "list", "utility", "sd15", "main", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderSD15MainModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD1.5 main model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.main_model,
        ui_order=1,
        ui_type=UIType.MainModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_sdxl_main_model",
    title="Field List Builder - SDXL Main Model",
    tags=["json", "field", "workflow", "list", "utility", "sdxl", "main", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderSDXLMainModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL main model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.sdxl_main_model,
        ui_order=1,
        ui_type=UIType.SDXLMainModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_sd3_main_model",
    title="Field List Builder - SD3 Main Model",
    tags=["json", "field", "workflow", "list", "utility", "sd3", "main", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderSD3MainModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD3 main model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.sd3_model,
        ui_order=1,
        ui_type=UIType.SD3MainModel,
        input=Input.Direct,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_clip_l_model",
    title="Field List Builder - CLIP-L Model",
    tags=["json", "field", "workflow", "list", "utility", "clip-l", "model", "encoder"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderCLIPLModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-L model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.clip_embed_model,
        ui_order=1,
        ui_type=UIType.CLIPLEmbedModel,
        input=Input.Direct,
        title="CLIP L Encoder",
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_clip_g_model",
    title="Field List Builder - CLIP-G Model",
    tags=["json", "field", "workflow", "list", "utility", "clip-g", "model", "encoder"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderCLIPGModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-G model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.clip_g_model,
        ui_order=1,
        ui_type=UIType.CLIPGEmbedModel,
        input=Input.Direct,
        title="CLIP G Encoder",
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_t2i_adapter",
    title="Field List Builder - T2I-Adapter",
    tags=["json", "field", "workflow", "list", "utility", "t2i", "adapter"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderT2IAdapterInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a T2I-Adapter model.
    """

    model: ModelIdentifierField = InputField(
        description="The T2I-Adapter model.",
        title="T2I-Adapter Model",
        ui_order=1,
        ui_type=UIType.T2IAdapterModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_vae_model",
    title="Field List Builder - VAE Model",
    tags=["json", "field", "workflow", "list", "utility", "vae", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderVAEModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model (SD1.5, SDXL, SD3 compatible).
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.vae_model,
        title="VAE",
        ui_order=1,
        ui_type=UIType.VAEModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_scheduler",
    title="Field List Builder - Scheduler",
    tags=["json", "field", "workflow", "list", "utility", "scheduler"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderSchedulerInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for a scheduler.
    """

    value: SCHEDULER_NAME_VALUES = InputField(
        default="euler",
        description=FieldDescriptions.scheduler,
        ui_order=1,
        ui_type=UIType.Scheduler,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


@invocation(
    "field_list_builder_sdxl_refiner",
    title="Field List Builder - SDXL Refiner Model",
    tags=["json", "field", "workflow", "list", "utility", "sdxl", "refiner", "model"],
    category="utilities",
    version="1.0.0"
)
class FieldListBuilderSDXLRefinerModelInvocation(FieldListBuilderInvocation):
    """
    Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL Refiner model.
    """

    model: ModelIdentifierField = InputField(
        description=FieldDescriptions.sdxl_refiner_model,
        ui_order=1,
        ui_type=UIType.SDXLRefinerModel,
    )

    def invoke(self, context: InvocationContext) -> StringOutput:
        return_value: StringOutput = super().invoke(context)
        return return_value


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
