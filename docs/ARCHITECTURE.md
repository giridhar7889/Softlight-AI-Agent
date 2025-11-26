# SoftLight Architecture

## Overview

SoftLight is a modular AI-powered system for automatically capturing UI workflows. The architecture follows a clean separation of concerns with five core components working together orchestrated by a central controller.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User / CLI                            │
│                    (main.py entry point)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Workflow Orchestrator                       │
│  • Coordinates all components                                │
│  • Manages workflow lifecycle                                │
│  • Controls execution loop                                   │
└───┬──────────────┬──────────────┬──────────────┬────────────┘
    │              │              │              │
    ▼              ▼              ▼              ▼
┌───────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
│Browser│    │   LLM    │   │    UI    │   │  State   │
│Control│    │  Agent   │   │ Detector │   │ Manager  │
│       │    │          │   │          │   │          │
└───┬───┘    └────┬─────┘   └────┬─────┘   └────┬─────┘
    │             │              │              │
    │             │              │              │
    └─────────────┴──────────────┴──────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   App Adapters  │
         │  (Linear, etc)  │
         └─────────────────┘
```

## Core Components

### 1. Browser Controller (`browser_controller.py`)

**Responsibility**: Low-level browser automation

**Key Features**:
- Playwright-based browser control
- Element interaction (click, type, hover, scroll)
- Screenshot capture
- Page information extraction
- Accessibility tree access

**Interface**:
```python
class BrowserController:
    async def navigate(url: str) -> bool
    async def click_element(selector: str) -> bool
    async def type_text(selector: str, text: str) -> bool
    async def take_screenshot() -> Image
    async def get_page_info() -> dict
```

### 2. LLM Agent (`llm_agent.py`)

**Responsibility**: AI-powered decision making

**Key Features**:
- Vision-based UI understanding
- Action decision logic
- Supports OpenAI GPT-4V and Anthropic Claude
- Contextual reasoning
- UI state description generation

**Interface**:
```python
class LLMAgent:
    async def analyze_ui(
        screenshot: Image,
        task_query: str,
        page_info: dict,
        previous_actions: List[Action]
    ) -> Action
    
    async def describe_ui_state(
        screenshot: Image,
        task_query: str
    ) -> str
```

**Action Types**:
- `click` - Click an element
- `type` - Enter text
- `press_key` - Press keyboard key
- `hover` - Hover over element
- `scroll` - Scroll page
- `wait` - Wait for stability
- `done` - Task complete
- `navigate` - Navigate to URL

### 3. UI Change Detector (`ui_detector.py`)

**Responsibility**: Detect significant UI changes

**Key Features**:
- Perceptual hashing (fast)
- Structural similarity (accurate)
- Configurable threshold
- State history tracking
- Diff visualization

**Detection Methods**:
1. **Hash-based**: Fast perceptual hashing using pHash
2. **Structural**: SSIM (Structural Similarity Index) for accuracy

**Interface**:
```python
class UIChangeDetector:
    def should_capture(
        screenshot: Image,
        force: bool = False
    ) -> (bool, float, str)
    
    def detect_change(
        image1: Image,
        image2: Image,
        threshold: float
    ) -> (bool, float)
```

### 4. State Manager (`state_manager.py`)

**Responsibility**: Capture and persist workflow data

**Key Features**:
- Screenshot storage
- Metadata management
- Workflow organization
- Dataset export
- README generation

**Data Structure**:
```
dataset/
├── {app_name}/
│   └── {task_id}_{timestamp}/
│       ├── step_01_navigate.png
│       ├── step_02_click.png
│       ├── step_03_type.png
│       ├── metadata.json
│       └── README.md
```

**Interface**:
```python
class StateManager:
    def start_workflow(app_name: str, task_id: str) -> Path
    def capture_step(screenshot: Image, description: str, ...) -> CapturedStep
    def end_workflow(success: bool) -> WorkflowDataset
```

### 5. Workflow Orchestrator (`orchestrator.py`)

**Responsibility**: Coordinate all components

**Execution Loop**:
```python
1. Initialize components
2. Navigate to start URL
3. Capture initial state
4. Loop until done or max steps:
   a. Take screenshot
   b. Get LLM decision
   c. Execute action
   d. Wait for stability
   e. Check UI change
   f. Capture if changed
5. Finalize dataset
```

**Interface**:
```python
class WorkflowOrchestrator:
    async def execute_workflow(
        task_query: str,
        task_id: str,
        start_url: str,
        max_steps: int
    ) -> WorkflowDataset
```

## App Adapters

App adapters provide application-specific logic:

### Base Adapter (`base_adapter.py`)

Abstract interface for all adapters:
- Authentication handling
- App-specific context
- Common selectors
- Element hints for tasks
- Pre/post task hooks

### Implementation Example (Linear)

```python
class LinearAdapter(BaseAdapter):
    def get_base_url() -> str
    async def setup_authentication(page: Page) -> bool
    def get_element_hints(task_query: str) -> dict
```

## Data Flow

### 1. Task Execution Flow

```
User Input (CLI)
    ↓
Load Configuration
    ↓
Initialize Orchestrator
    ↓
Start Browser + LLM Agent
    ↓
Execute Workflow Loop:
    • Screenshot → LLM → Action → Execute
    • UI Change Detection
    • State Capture (if changed)
    ↓
Save Dataset
    ↓
Generate README + Metadata
```

### 2. Screenshot Capture Decision

```
Action Executed
    ↓
Wait for UI Stability
    ↓
Take Screenshot
    ↓
Compare with Previous (Hash/SSIM)
    ↓
Difference >= Threshold?
    ├─ Yes → Capture + Save
    └─ No  → Skip
```

### 3. LLM Decision Making

```
Current Screenshot
    +
Task Query
    +
Page Info (URL, title)
    +
Previous Actions
    ↓
LLM Vision Analysis
    ↓
JSON Response:
{
  "action_type": "click",
  "description": "Click Create Project",
  "selector": "button:has-text('Create')",
  "reasoning": "..."
}
```

## Configuration System

### App Configuration (`config/apps.yaml`)

```yaml
linear:
  base_url: "https://linear.app"
  workspace: "test916"
  wait_after_action: 1.0
  change_threshold: 0.15
  selectors:
    create_project: "button:has-text('New project')"
```

### Task Configuration (`config/tasks.yaml`)

```yaml
tasks:
  - id: "linear_create_project"
    app: "linear"
    query: "How do I create a project in Linear?"
    max_steps: 10
    start_url: "https://linear.app/..."
```

## Scalability Considerations

### 1. Modularity
- Each component is independent
- Easy to swap implementations
- Clean interfaces

### 2. Extensibility
- Plugin-based adapter system
- Configurable thresholds
- Multiple LLM providers

### 3. Performance
- Async/await throughout
- Fast hash-based change detection
- Efficient screenshot handling

### 4. Reliability
- Retry logic with exponential backoff
- Graceful error handling
- Timeout protection

## Key Design Patterns

### 1. Adapter Pattern
App-specific logic isolated in adapters

### 2. Strategy Pattern
Different change detection methods (hash vs structural)

### 3. Observer Pattern
UI changes trigger capture events

### 4. Template Method
Base adapter defines workflow, subclasses customize

## Future Enhancements

### Potential Improvements:

1. **Parallel Execution**: Run multiple tasks concurrently
2. **Smart Element Detection**: Computer vision for element finding
3. **Learning System**: Improve from previous captures
4. **Cloud Storage**: S3/GCS integration for datasets
5. **API Mode**: REST API for remote execution
6. **Interactive Mode**: Human-in-the-loop corrections
7. **Video Capture**: Record full video alongside screenshots
8. **Multi-browser**: Support Firefox, Safari
9. **Mobile Support**: iOS/Android app automation
10. **A/B Testing**: Capture variations

## Error Handling Strategy

### Levels of Recovery:

1. **Action Level**: Retry failed actions
2. **Step Level**: Skip and continue
3. **Workflow Level**: Graceful termination
4. **System Level**: Cleanup and logging

### Error Types:

- **Recoverable**: Element not found, timeout
- **Critical**: Browser crash, API failure
- **User**: Invalid configuration

## Testing Strategy

### Unit Tests
- Individual component logic
- Mock external dependencies

### Integration Tests
- Component interaction
- End-to-end workflows

### Test Apps
- Local test pages
- Controlled environments

## Security Considerations

1. **Credentials**: Environment variables only
2. **Sandboxing**: Browser isolation
3. **Data Privacy**: Local storage default
4. **API Keys**: Never committed to git
5. **Rate Limiting**: Respect API limits

## Performance Metrics

### Key Metrics to Track:

- **Capture Accuracy**: % of relevant states captured
- **False Positives**: % of unnecessary captures
- **Execution Time**: Time per workflow
- **LLM Calls**: Number of API calls
- **Success Rate**: % of completed workflows

---

This architecture provides a solid foundation for generalizable UI workflow capture while remaining maintainable and extensible.

