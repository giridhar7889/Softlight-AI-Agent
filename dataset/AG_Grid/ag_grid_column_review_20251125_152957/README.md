# AG Grid: Quick filter Spanish, hide the Rating column via column panel, then restore it

## Workflow Information

- **Task ID**: ag_grid_column_review
- **App**: Linear
- **Timestamp**: 2025-11-25T15:29:57.752716
- **Duration**: 10.38 seconds
- **Total Steps**: 4
- **Status**: ✅ Success

## Steps

### Step 1: Opened AG Grid demo landing page

- **Action**: navigate
- **Target**: https://www.ag-grid.com/example/
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_01_navigate.png`
- **Reasoning**: Baseline view before filtering and toggling columns

### Step 2: Applied global quick filter for 'Spanish'

- **Action**: filter
- **Target**: #global-filter
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_02_filter.png`
- **Reasoning**: Shows only the Spanish-related rows in the grid

### Step 3: Hid the Rating column via the column tool panel

- **Action**: hide-column
- **Target**: Column tool panel toggle
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_03_hide-column.png`
- **Reasoning**: Removes the Rating column from the Spanish-focused view

### Step 4: Restored the Rating column

- **Action**: show-column
- **Target**: Column tool panel toggle
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_04_show-column.png`
- **Reasoning**: Brings Rating back into the grid after review

