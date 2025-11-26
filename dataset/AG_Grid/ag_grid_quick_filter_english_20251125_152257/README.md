# AG Grid: Use global filter to show rows containing English

## Workflow Information

- **Task ID**: ag_grid_quick_filter_english
- **App**: Linear
- **Timestamp**: 2025-11-25T15:22:57.149517
- **Duration**: 6.00 seconds
- **Total Steps**: 3
- **Status**: ✅ Success

## Steps

### Step 1: Opened AG Grid example landing page

- **Action**: navigate
- **Target**: https://www.ag-grid.com/example/
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_01_navigate.png`
- **Reasoning**: Baseline state before using the global filter

### Step 2: Applied global quick filter for 'English'

- **Action**: filter
- **Target**: #global-filter
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_02_filter.png`
- **Reasoning**: Typed 'English' in the global filter to show only matching rows

### Step 3: Verified filtered results show English entries

- **Action**: info
- **Target**: First visible row after filtering
- **URL**: https://www.ag-grid.com/example/
- **Screenshot**: `step_03_info.png`
- **Reasoning**: Top visible language cell reads 'English' after filtering

