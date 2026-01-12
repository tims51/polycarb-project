# Implementation Plan

## 1. Mother Liquor Management Updates
### `app/page_modules/data_recording.py`
- **Modify `_render_mother_liquor_tab`**:
    - Update `source_type` radio button options to: `["合成实验", "外来样品", "大生产母液"]`.
    - Implement logic for the "大生产母液" (Mass Production) option:
        - Add input fields:
            - **Production Date** (`production_date`): Date input.
            - **Batch Number** (`batch_number`): Text input.
            - **Mother Liquor Name** (`ml_name`): Text input.
            - **Production Mode** (`production_mode`): Select/Radio with options `["工厂自产", "代工生产"]`.
            - **Manufacturer** (`manufacturer`): Text input, visible only if "代工生产" is selected.
        - Reuse common fields: Solid Content, pH, Density, Color, Description.
    - Update the **Save Logic** to handle the new fields (`batch_number`, `production_date`, `production_mode`, `manufacturer`) and store them in the mother liquor record.
    - Update the **List/Table View** to display these new details (Batch No, Manufacturer) for mass production items.
    - Update the **Detail View** to show the new fields.

## 2. Paste Experiment Updates
### `app/page_modules/data_recording.py`
- **Modify `_render_paste_experiments_tab`**:
    - **Expand Associated Formula Options**:
        - Currently, it fetches `synthesis_records` and `products`.
        - Add logic to fetch `mother_liquors` using `data_manager.get_all_mother_liquors()`.
        - Update `paste_formula_options` to include entries formatted as `f"母液: {ml['name']} (ID:{ml['id']})"`.
    - **Add Mother Liquor Feedback Fields**:
        - Inside the form, add a new section "🧪 母液性质复测" (Mother Liquor Properties Verification).
        - Add input fields for:
            - **Solid Content** (`ml_solid_content`): Number input.
            - **Density** (`ml_density`): Number input.
            - **pH** (`ml_ph`): Number input.
        - *Note*: These fields should likely be auto-filled if a Mother Liquor is selected (by looking up the ML's current values), but editable for the actual measured values in this experiment.
    - **Update Save Logic**:
        - When saving the paste experiment:
            - Check if the selected `formula_name` corresponds to a Mother Liquor (parse the ID).
            - If it is a Mother Liquor:
                - Extract the measured Solid Content, Density, and pH from the form.
                - Call `data_manager.update_mother_liquor(ml_id, updates)` to update the mother liquor's properties with these new test results.
                - Add a note or flag in the Paste Experiment record indicating which Mother Liquor ID was updated.

## 3. Data Manager Updates (if needed)
- `app/core/data_manager.py`:
    - Ensure `update_mother_liquor` exists and works as expected (already verified in previous turns, but good to double-check).
    - Ensure `get_all_mother_liquors` is available (already verified).

## 4. Execution Order
1.  Update `_render_mother_liquor_tab` to support "Mass Production" source.
2.  Update `_render_paste_experiments_tab` to include Mother Liquors in selection.
3.  Add properties input fields to Paste Experiment form.
4.  Implement the feedback loop to update Mother Liquor data upon saving Paste Experiment.
