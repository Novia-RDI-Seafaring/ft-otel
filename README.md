# FastHTML OpenTelemetry Streamer

Real-time OpenTelemetry streaming components for FastHTML applications. Stream telemetry data as beautiful, nested, collapsible components that update live as spans are created and completed.

## Features

- **One-line setup**: Add real-time telemetry streaming with a single function call
- **Beautiful UI**: Collapsible, nested span visualization with status colors
- **Real-time updates**: See spans appear and update live via Server-Sent Events
- **Thread-safe**: Works seamlessly with any OpenTelemetry instrumentation
- **Customizable**: Bring your own renderers or extend the defaults
- **AI-optimized**: Specialized rendering for AI/LLM spans with rich metrics
- **Attribute-based rendering**: Custom renderers for specific span types
- **Zero config**: Sensible defaults, optional customization

## Quick Start

```python
from fasthtml.common import *
import fasthtml_otel as ft_otel
from opentelemetry.sdk.trace import TracerProvider

# Create your FastHTML app
app = FastHTML()

# Set up OpenTelemetry
provider = TracerProvider()
ft_otel.configure(app, provider)

# Your routes automatically get telemetry
@app.get("/")
def index():
    return Div(
        H1("My App"),
        ft_otel.telemetry_container(),
    )

serve()
```

That's it! Visit your app and you'll see live telemetry data streaming in.

## Installation

```bash
pip install fasthtml-otel
```

## Advanced Usage

### Custom Container

```python
import fasthtml_otel as ft_otel
from opentelemetry.sdk.trace import TracerProvider

# Configure with custom container ID and AI renderer
provider = TracerProvider()
ft_otel.configure(
    app, provider,
    container_id="my-telemetry",
    attribute_renderers={
        "gen_ai.operation.name": ft_otel.AISpanRenderer()
    }
)

@app.get("/")
def index():
    return Div(
        H1("My App"),
        ft_otel.telemetry_container(title="Custom Telemetry"),
    )
```

### Custom Renderers

```python
import fasthtml_otel as ft_otel
from fasthtml_otel.renderers import SpanRenderer
from opentelemetry.sdk.trace import TracerProvider

class MySpanRenderer(SpanRenderer):
    def render_header(self, span):
        return Div(f"SPAN: {span.name}", cls="custom-header")

provider = TracerProvider()
ft_otel.configure(app, provider, renderer=MySpanRenderer())
```

### Integration with Existing Telemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
import fasthtml_otel as ft_otel

# Set up your existing OpenTelemetry
provider = TracerProvider()
# Don't set global provider yet - let ft_otel.configure() do it

# Add FastHTML streaming
ft_otel.configure(app, provider)
```

## Example with Manual Tracing

```python
from fasthtml.common import *
import fasthtml_otel as ft_otel
from opentelemetry.sdk.trace import TracerProvider

app = FastHTML()
provider = TracerProvider()
ft_otel.configure(app, provider)

# Get a tracer for manual instrumentation
tracer = provider.get_tracer("my-app")

@app.get("/")
def index():
    return Div(
        H1("Telemetry Demo"),
        Button("Trigger Operation", hx_post="/process", hx_target="#result"),
        Div(id="result"),
        ft_otel.telemetry_container(),
    )

@app.post("/process")
def process():
    with tracer.start_as_current_span("user_operation") as span:
        span.set_attribute("operation.type", "data_processing")

        # Simulate some work with nested spans
        with tracer.start_as_current_span("validate_data") as validate_span:
            validate_span.set_attribute("data.size", 1024)
            import time
            time.sleep(0.1)  # Simulate validation work

        with tracer.start_as_current_span("process_data") as process_span:
            process_span.set_attribute("algorithm", "example")
            time.sleep(0.2)  # Simulate processing work

        span.set_attribute("success", True)

    return Div("Operation completed! Check the telemetry panel.", cls="text-green-600")
```

## Example with Pydantic AI

```python
from fasthtml.common import *
import fasthtml_otel as ft_otel
from opentelemetry.sdk.trace import TracerProvider
from pydantic_ai import Agent

app = FastHTML()
provider = TracerProvider()
ft_otel.configure(
    app, provider,
    attribute_renderers={
        "gen_ai.operation.name": ft_otel.AISpanRenderer(auto_expand_patterns=["chat", "Tool:"])
    }
)

# Instrument Pydantic AI (renderer-agnostic)
ft_otel.instrument_pydantic_ai(provider)
agent = Agent("gpt-4o-mini")

@app.get("/")
def index():
    return Div(
        H1("Chat App"),
        ft_otel.telemetry_container(),
    )

@app.post("/chat")
def chat(msg: str):
    result = agent.run(msg)
    return Div(result.data)
```

### Attribute-Based Custom Renderers

```python
# Configure with attribute-based renderers
ft_otel.configure(
    app, provider,
    attribute_renderers={
        "gen_ai.operation.name": ft_otel.AISpanRenderer(),
        "db.operation": MyDatabaseRenderer(),
        "http.method": HttpSpanRenderer()
    }
)

# Or register individually after configuration
ft_otel.register_attribute_renderer("custom.span.type", CustomRenderer())
```

## Development

```bash
git clone https://github.com/Novia-RDI-Seafaring/ft-otel
cd ft-otel
pip install -e ".[dev]"

# Run main example
cd example
python app.py

# Run AI-focused example
python ai_example.py --port 8003
```

## Citation

If you use this software in your research or projects, please cite it as:

```bibtex
@software{fasthtml_otel,
  title={FastHTML OpenTelemetry Streamer},
  author={Christoffer Björkskog},
  year={2025},
  url={https://github.com/Novia-RDI-Seafaring/ft-otel}
}
```

## Acknowledgments

This project is part of the [Virtual Sea Trial Project (VST)](https://virtualseatrial.fi/), funded by Business Finland.

## License

MIT License - see LICENSE file for details.