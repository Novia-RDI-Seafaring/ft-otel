# FastHTML OpenTelemetry Example

This example demonstrates how to use `fasthtml-otel` to add real-time OpenTelemetry streaming to your FastHTML applications.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the example:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   Visit http://localhost:8000 to see the demo

## What You'll See

- **Real-time telemetry streaming**: Watch OpenTelemetry spans appear and update live
- **Nested span visualization**: See parent-child relationships in collapsible UI
- **Interactive demos**: Buttons to create test traces and simulate operations
- **AI chat integration**: Chat with Pydantic AI and see the telemetry (if pydantic-ai is installed)

## Try These Features

1. **Click "Create Test Traces"** - See nested database and cache operations
2. **Click "Slow Operation"** - Watch a multi-step process with timing
3. **Chat with AI** (if available) - See LLM calls traced in real-time
4. **Navigate pages** - Every page load creates traces

## Code Highlights

### One-Line Setup
```python
from fasthtml_otel import otel_streamer

app = FastHTML()
otel_streamer(app)  # That's it!
```

### Custom Container
```python
streamer = otel_streamer(app)

@app.get("/")
def index():
    return Div(
        streamer.create_container(title="My Telemetry"),
        # ... rest of your page
    )
```

### Manual Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.get("/api")
def api_endpoint():
    with tracer.start_as_current_span("api_call") as span:
        span.set_attribute("endpoint", "/api")
        # Your logic here
        return {"status": "ok"}
```

## Integration Examples

### With Existing OpenTelemetry
```python
from opentelemetry.sdk.trace import TracerProvider

# Your existing setup
provider = TracerProvider()
trace.set_tracer_provider(provider)

# Add FastHTML streaming
otel_streamer(app, tracer_provider=provider)
```

### Custom Renderers
```python
from fasthtml_otel.renderers import SpanRenderer

class MyRenderer(SpanRenderer):
    def render_header(self, span):
        return Div(f"🔥 {span.name}")

otel_streamer(app, renderer=MyRenderer())
```

## Customization

The example uses DaisyUI for styling, but you can customize:

- **Container styling**: Pass `cls` parameter to `create_container()`
- **Renderer**: Create custom `SpanRenderer` subclass
- **Theme**: DaisyUI themes work out of the box
- **Layout**: Place the telemetry container anywhere in your layout

## What's Happening

1. **Automatic instrumentation**: FastHTML routes are automatically traced
2. **Real-time streaming**: Spans stream via Server-Sent Events as they happen
3. **Nested display**: Parent-child relationships shown with collapsible UI
4. **Live updates**: Spans update when they complete with final timing/status

Used for debugging, monitoring, and understanding your application flow!