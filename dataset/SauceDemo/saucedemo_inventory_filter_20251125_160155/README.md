# SauceDemo: Sort inventory by price (high to low) and add cheapest item from the sorted view

## Workflow Information

- **Task ID**: saucedemo_inventory_filter
- **App**: Linear
- **Timestamp**: 2025-11-25T16:01:55.194132
- **Duration**: 3.62 seconds
- **Total Steps**: 4
- **Status**: ✅ Success

## Steps

### Step 1: Logged in and reached inventory list

- **Action**: login
- **Target**: Inventory container
- **URL**: https://www.saucedemo.com/inventory.html
- **Screenshot**: `step_01_login.png`
- **Reasoning**: Baseline before sorting

### Step 2: Sorted inventory by price high to low

- **Action**: sort
- **Target**: Sorting dropdown
- **URL**: https://www.saucedemo.com/inventory.html
- **Screenshot**: `step_02_sort.png`
- **Reasoning**: Inventory order now shows most expensive items first

### Step 3: Added the cheapest item after sorting

- **Action**: add-to-cart
- **Target**: Last item's Add to Cart button
- **URL**: https://www.saucedemo.com/inventory.html
- **Screenshot**: `step_03_add-to-cart.png`
- **Reasoning**: Demonstrates grabbing the least expensive product from the sorted view

### Step 4: Viewed cart to confirm cheapest item was added

- **Action**: cart
- **Target**: Cart page
- **URL**: https://www.saucedemo.com/cart.html
- **Screenshot**: `step_04_cart.png`
- **Reasoning**: Cart badge and line item confirm the action

