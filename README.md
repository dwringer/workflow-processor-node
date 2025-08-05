# workflow-processor-node

**Repository Name:** InvokeAI Workflow Processor Node (Enqueue [Image] Workflow Batch)

**Author:** dwringer

**License:** MIT

**Requirements:**
- invokeai>=4

## Introduction
This InvokeAI node pack introduces the concept of *workflow chaining*, enabling dynamic input passing from parent to child workflows. This embeds generation parameters directly into child workflow input forms, making reproducing a given image generation (from dynamic prompts, seeds, parameters, models, etc) a single click operation, using the workflow loaded from that image through right-clicking on it in the UI.

### Benefits:
* **Modular Workflow Design:** Workflows function as reusable "black boxes" for self-contained, multi-stage generation components.
* **Sequential Callback Chains:** Child workflows can enqueue further workflows for complex multi-stage processing, or even conditional branching.
* **Improved UI Responsiveness:** Break down large graphs into smaller, focused units, preventing UI slowdowns and keeping input latency (not to mention user cognitive load) to a minimum.
* **Direct Reproducibility:** Generation parameters are baked in to child workflows, allowing effortless recall and reproduction of specific results. Change the model, prompt, or other parameters on any output image's embedded workflow for immediate variations, without having to recall any metadata or re-input any values.

### How it works:

InvokeAI workflows already utilize a form builder to expose fields in a linear user interface. This node set leverages those forms to create an interface abstraction for enqueuing the execution of one workflow from within another using the **Enqueue Workflow Batch** or **Enqueue Image Workflow Batch** nodes\*.

Users define each stage's input and output interfaces in terms of the form builder and this repository's corresponding **Field List Builder** nodes. Through these, stages can be chained, with each sequentially passing outputs (and/or additional fields inherited from its parent) to the subsequent stage's input form.

\**Note on the use of the term "batch": while InvokeAI's *"Batch Generator"* nodes typically queue multiple distinct invocations, the "Batch" in this pack's node names refers to the underlying* `/api/v1/queue/enqueue_batch` *API endpoint used for *any* generation request. Currently, execution of these nodes enqueues a *single* modified workflow instance.*

### Further details:

The *Enqueue Workflow Batch* and *Enqueue Image Workflow Batch* nodes each operate by applying user updates to a pre-defined workflow and sending it directly to the InvokeAI backend API. The first node can load workflows from saved workflow JSON files or saved browser enqueue_batch request payloads, while the second loads workflows directly from InvokeAI images (these are embedded by default in every image saved to the gallery). The nodes generate a schema from the loaded workflow input form then use that to validate an ordered list, provided as another node input, used to update values in the workflow graph. That list can be structured such as:
```
[
 {"prompt": "a portrait of a housecat wearing a tie and business attire"},
 {"value": 1728},
 {"value": 1152},
 {"seed": 700},
 {"num_steps": 4}
]
```

These JSON structures can be input directly as strings, or created with a set of Field List Builder nodes. Every Field List Builder node has one `value` output and three inputs: `existing_json`, `field_name`, and `value`. These nodes are chained together by connecting the `value` output of one to the `existing_json` input of another, by which they can be sequenced in the order they appear in the workflow's linear UI panel.

Note that field names given can be either the base name as defined in the node itself, or the user-applied label (if it has been renamed). Either will work, with spaces or underscores, and is case insensitive. Duplicate names are no problem as long as they are properly ordered in the input updates JSON.

To populate EnumFields, simply use strings, and just make sure to type the value exactly as it appears in the enum.

##### Workflow payload creation

To make a workflow available to load by filename, download it from the Invoke UI (as a .json file) and place it in this node's `workflow_payloads` subdirectory. (`<invokeai-install-path>/nodes/workflow-processor-node/workflow_payloads/`). Remember, the Enqueue Image Workflow Batch node can also just load the embedded workflow out of any InvokeAI image saved to the gallery.

### Installation:

To install these nodes, simply place the folder containing this repository's code (or just clone the repository yourself) into your `invokeai/nodes` folder.

### Getting started:
To help you get up and running quickly, this pack includes some example workflows and animated demonstrations. You'll find the workflow files in the `workflow_payloads` subdirectory of the node pack's folder. These examples illustrate both the creation of simple workflow UIs and the calling of one workflow from another.

#### Visual Guide (Animated Demos - click to view)

<details>
<summary>Building a Linear UI Form</summary>

This GIF demonstrates the process of creating a simple generation graph and then using the InvokeAI UI to define a linear UI form for it. This form is what a parent workflow will use to pass in new parameters.
* **[Embed GIF 1 here]**

</details>

<details>
<summary>Creating a Calling Workflow</summary>

Watch this GIF to see a workflow enqueuing another workflow in action. It shows how the `Enqueue Workflow Batch` node is used to dynamically update parameters in a child workflow, baking them in for effortless reproducibility.
* **[Embed GIF 2 here]**

</details>

<details>
<summary>Multiple Workflow Processing</summary>

This advanced example shows the power of modular workflows. A single invocation of a calling workflow uses the `Enqueue Image Workflow Batch` node to send a prompt through three different generation workflows, each with additional extra context for creating thematic variations.
* **[Embed GIF 3 here]**

</details>

#### Example Workflows
The `workflow_payloads` subdirectory contains several example `.json` files for you to use and inspect. For our purposes these can be divided into two categories: 'Target Workflows' (the generations that are being called) and 'Calling Workflows' (the parent workflows that initiate the calls).

<details>

<summary>Target Workflows (click to expand)</summary>

###### SD 1.5 Generation
This workflow file (`example_sd15_payload_1.json`) is a basic text-to-image setup for an SD1.5 model. It's designed to be called by a parent workflow and has a simple linear UI form to expose core parameters like prompt, seed, and image dimensions.
###### SDXL Generation
Similar to the SD1.5 example, this workflow (`example_sdxl_payload_1.json`) is configured for the SDXL model. It includes additional nodes and parameters to handle the SDXL model's specific requirements.
###### FLUX.1 Generation
This workflow (`example_flux_payload_1.json`) is a simple setup for the FLUX.1 model, ready to be called by a parent workflow. It is also the target for the 'preset' example to show how parameters can be easily swapped.

</details>

<details>

<summary>Calling Workflows (click to expand)</summary>

###### SD1.5 Calling Workflow
This example (`parent_example_sd15_workflow.json`) demonstrates how to call the SD1.5 target workflow, passing in a prompt and other parameters via a `Field List Builder` chain.
###### SDXL Calling Workflow
This example (`parent_example_sdxl_workflow.json`) shows how to call the SDXL target workflow. It highlights how to handle a more complex set of parameters for a larger model.
###### FLUX.1 Calling Workflow
This workflow (`parent_example_flux_workflow.json`) is configured to call the FLUX.1 target workflow. It serves as the base for the 'presets' example and shows how a different model can be called with the same core node pack.
###### FLUX.1 Preset Calling Workflow
This example (`parent_example_flux_workflow_presets.json`) demonstrates a powerful use case: using a JSON string as a 'preset.' It shows how a single parent workflow can be configured to generate images in different sizes or aspect ratios (e.g., 'Portrait' or 'Landscape') by simply swapping out a JSON string fed into the `Enqueue Workflow Batch` node.

</details>

#### Known Issues & Limitations

* **Batch Generation Control:** The *Enqueue Workflow Batch* node currently enqueues only a single execution of a saved workflow, regardless of whether that workflow was originally designed to run as a batch. While the target workflow will still execute as a batch if configured to do so, its batch parameters cannot be dynamically adjusted via these nodes. Future support for controlling batch generation through these nodes may be considered based on user demand.
* **"Board: Auto" Behavior:** If a saved workflow payload was configured with a "Board: Auto" setting, its generated images will default to the board it was targeting when originally created. To ensure generated images from a child workflow are directed to the currently active "AUTO" board in the UI, parent workflows must explicitly send a *Field List Builder - Board* node, set to "Auto," into the *Enqueue Workflow Batch* node, with a corresponding board field added to the child workflow's linear UI form.

## Overview
### Nodes
- [Enqueue Image Workflow Batch](#enqueue-image-workflow-batch) - Enqueues a workflow batch by extracting the 'invokeai_workflow' JSON string
- [Enqueue Workflow Batch](#enqueue-workflow-batch) - Enqueues a workflow batch by applying user updates to a pre-defined payload
- [Field List Builder - Board](#field-list-builder---board) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Boolean](#field-list-builder---boolean) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - CLIP Model](#field-list-builder---clip-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP embed model.
- [Field List Builder - CLIP-G Model](#field-list-builder---clip-g-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-G model.
- [Field List Builder - CLIP-L Model](#field-list-builder---clip-l-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-L model.
- [Field List Builder - ControlLoRA](#field-list-builder---controllora) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - ControlNet](#field-list-builder---controlnet) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Float](#field-list-builder---float) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Float Collection](#field-list-builder---float-collection) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - FLUX Main Model](#field-list-builder---flux-main-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a main model.
- [Field List Builder - FLUX Redux Model](#field-list-builder---flux-redux-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a FLUX Redux model.
- [Field List Builder - FLUX VAE](#field-list-builder---flux-vae) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model.
- [Field List Builder - Image](#field-list-builder---image) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Image Collection](#field-list-builder---image-collection) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Integer](#field-list-builder---integer) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Integer Collection](#field-list-builder---integer-collection) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - IP Adapter](#field-list-builder---ip-adapter) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Join](#field-list-builder---join) - Concatenates two JSON lists.
- [Field List Builder - LoRA](#field-list-builder---lora) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - Scheduler](#field-list-builder---scheduler) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a scheduler.
- [Field List Builder - SD1.5 Main Model](#field-list-builder---sd15-main-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD1.5 main model.
- [Field List Builder - SD3 Main Model](#field-list-builder---sd3-main-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD3 main model.
- [Field List Builder - SDXL Main Model](#field-list-builder---sdxl-main-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL main model.
- [Field List Builder - SDXL Refiner Model](#field-list-builder---sdxl-refiner-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL Refiner model.
- [Field List Builder - String](#field-list-builder---string) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - String Collection](#field-list-builder---string-collection) - Builds or appends to a JSON list containing single key-value pair dictionaries.
- [Field List Builder - T2I-Adapter](#field-list-builder---t2i-adapter) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a T2I-Adapter model.
- [Field List Builder - T5 Model](#field-list-builder---t5-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a T5 encoder model.
- [Field List Builder - VAE Model](#field-list-builder---vae-model) - Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model (SD1.5, SDXL, SD3 compatible).

<details>
<summary>

### Functions

</summary>

- `transform_workflow_to_payload` - Transforms the JSON structure from a workflow format to a batched payload format.
- `_get_workflow_processor_from_content` - 
</details>

<details>
<summary>

### Output Definitions

</summary>

- `EnqueueWorkflowBatchOutput` - Output definition with 2 fields
</details>

## Nodes
### Enqueue Image Workflow Batch
**ID:** `enqueue_image_workflow_batch`

**Category:** system

**Tags:** batch, workflow, automation, api, image, metadata

**Version:** 1.0.0

**Description:** Enqueues a workflow batch by extracting the 'invokeai_workflow' JSON string

from an input image's metadata, applying user updates, and sending it directly
    to the InvokeAI backend API using http.client.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `image` | `ImageField` | The image containing the 'invokeai_workflow' JSON string in its metadata. | None |


</details>

<details>
<summary>

#### Output

</summary>

**Type:** `self._process_and_enqueue(...)`



</details>

---
### Enqueue Workflow Batch
**ID:** `enqueue_workflow_batch`

**Category:** system

**Tags:** batch, workflow, automation, api

**Version:** 1.0.0

**Description:** Enqueues a workflow batch by applying user updates to a pre-defined payload

from a file and sending it directly to the InvokeAI backend API using http.client.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `workflow_payload_filename` | `str` | The filename of the enqueue_batch JSON payload (e.g., 'my_workflow_payload.json') located in the node's 'workflow_payloads' subdirectory. | None |


</details>

<details>
<summary>

#### Output

</summary>

**Type:** `EnqueueWorkflowBatchOutput`

| Name | Type | Description |
| ---- | ---- | ----------- |
| `status` | `str` | Status of the enqueue operation (e.g., 'Success', 'Failed') |
| `message` | `str` | A descriptive message about the enqueue operation. |


</details>

---
### Field List Builder - Board
**ID:** `field_list_builder_board`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, board

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Boolean
**ID:** `field_list_builder_boolean`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, boolean

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `bool` | The value for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - CLIP Model
**ID:** `field_list_builder_clip_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, clip, encoder

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP embed model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - CLIP-G Model
**ID:** `field_list_builder_clip_g_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, clip-g, model, encoder

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-G model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - CLIP-L Model
**ID:** `field_list_builder_clip_l_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, clip-l, model, encoder

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a CLIP-L model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - ControlLoRA
**ID:** `field_list_builder_controllora`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, controllora

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - ControlNet
**ID:** `field_list_builder_controlnet`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, controlnet

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Float
**ID:** `field_list_builder_float`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, float

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `float` | The value for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Float Collection
**ID:** `field_list_builder_float_collection`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, float, collection

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `collection` | `list[float]` | The collection for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - FLUX Main Model
**ID:** `field_list_builder_flux_main_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, flux, main, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a main model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - FLUX Redux Model
**ID:** `field_list_builder_flux_redux_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, flux, redux, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a FLUX Redux model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` | The FLUX Redux model to use. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - FLUX VAE
**ID:** `field_list_builder_flux_vae`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, vae, flux

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Image
**ID:** `field_list_builder_image`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, image

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `ImageField` | The value for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Image Collection
**ID:** `field_list_builder_image_collection`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, image, collection

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `collection` | `list[ImageField]` | The image collection for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Integer
**ID:** `field_list_builder_integer`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, integer

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `int` | The value for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Integer Collection
**ID:** `field_list_builder_integer_collection`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, integer, collection

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `collection` | `list[int]` | The collection for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - IP Adapter
**ID:** `field_list_builder_ip_adapter`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, ip, adapter

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Join
**ID:** `field_list_builder_join`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, join, concatenate

**Version:** 1.0.0

**Description:** Concatenates two JSON lists.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `first` | `str` | The first JSON field list for joining. | None |
| `second` | `str` | The second JSON field list for joining. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - LoRA
**ID:** `field_list_builder_lora`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, lora

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - Scheduler
**ID:** `field_list_builder_scheduler`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, scheduler

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a scheduler.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `SCHEDULER_NAME_VALUES` |  | euler |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - SD1.5 Main Model
**ID:** `field_list_builder_sd15_main_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, sd15, main, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD1.5 main model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - SD3 Main Model
**ID:** `field_list_builder_sd3_main_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, sd3, main, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for an SD3 main model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - SDXL Main Model
**ID:** `field_list_builder_sdxl_main_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, sdxl, main, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL main model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - SDXL Refiner Model
**ID:** `field_list_builder_sdxl_refiner`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, sdxl, refiner, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for an SDXL Refiner model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - String
**ID:** `field_list_builder_string`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, string

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `value` | `str` | The value for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - String Collection
**ID:** `field_list_builder_string_collection`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, string, collection

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `collection` | `list[str]` | The collection for the new entry. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - T2I-Adapter
**ID:** `field_list_builder_t2i_adapter`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, t2i, adapter

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a T2I-Adapter model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` | The T2I-Adapter model. | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - T5 Model
**ID:** `field_list_builder_t5_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, t5, encoder

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a T5 encoder model.

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---
### Field List Builder - VAE Model
**ID:** `field_list_builder_vae_model`

**Category:** utilities

**Tags:** json, field, workflow, list, utility, vae, model

**Version:** 1.0.0

**Description:** Builds or appends to a JSON list containing single key-value pair dictionaries, for a VAE model (SD1.5, SDXL, SD3 compatible).

<details>
<summary>

#### Inputs

</summary>

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `model` | `ModelIdentifierField` |  | None |


</details>

<details>
<summary>

#### Output

</summary>

No output information available.


</details>

---

## Footnotes
For questions/comments/concerns/etc, use github or drop into the InvokeAI discord where you'll probably find someone who can help.

