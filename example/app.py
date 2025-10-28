from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Resource
from pydantic_ai import Agent
import datetime

resource = Resource.create({"service.name": "Ft Otel Streamer Demo"})
provider = TracerProvider(resource=resource)


from fasthtml.common import *
import sys
sys.path.insert(0, '..')

import fasthtml_otel as ft_otel
from ai_renderer import AISpanRenderer

# Create FastHTML app
app = FastHTML(exts="ws")
streamer = ft_otel.configure(
    app,
    provider,
    auto_expand_patterns=["Tool:", "Chat Message:"],
    renderers=[
        AISpanRenderer(auto_expand_patterns=["agent run"])
    ]
)

# Instrument Pydantic AI (renderer-agnostic)
ft_otel.instrument_pydantic_ai(provider)

tracer = provider.get_tracer("Ft Otel Streamer Demo")




# Create instrumented agent
agent = Agent(
    "gpt-4o-mini",
    system_prompt="You are a helpful assistant that provides concise responses. always use tools if you can"
)
@agent.tool_plain()
def roll_dice(sides: int=6) -> str:
    """Roll a die and return the result."""
    global tracer
    import random
    with tracer.start_as_current_span("Tool: Roll a die", attributes={"sides": sides}) as span:
        # Fallback if no current span
        result = random.randint(1, sides)
        span.set_attribute("result", result)
        msg = f"You rolled a {result}"
        span.set_attribute("returning", msg)
        return msg

@agent.tool_plain()
def check_time() -> str:
    """Check the current time."""
    global tracer
    with tracer.start_as_current_span("Tool: Check the time") as span:
        t = datetime.datetime.now().strftime("%H:%M:%S")
        span.set_attribute("time", t)
        msg = f"The time is {t}"
        span.set_attribute("returning", msg)
        return msg


# Chat messages storage
messages = []

def ChatMessage(idx):
    """Render a chat message."""
    msg = messages[idx]
    bubble = "chat-bubble-primary" if msg["role"] == "user" else "chat-bubble-secondary"
    align = "chat-end" if msg["role"] == "user" else "chat-start"
    return Div(
        Div(msg["role"], cls="chat-header text-xs opacity-70"),
        Div(msg["content"], id=f"chat-content-{idx}", cls=f"chat-bubble {bubble}"),
        id=f"chat-message-{idx}",
        cls=f"chat {align}"
    )

def ChatInput():
    """Render chat input field."""
    return Input(
        type="text",
        name="msg",
        id="msg-input",
        placeholder="Ask me to roll a die...",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )

@app.ws("/ws")
async def chat_socket(msg: str, send):
    """Handle chat WebSocket messages."""
    print(f"Chat message: {msg}")
    tracer = provider.get_tracer("Ft Otel Streamer Demo")
    with tracer.start_as_current_span("Chat Message: " + msg.strip()[:10] + "...", attributes={"user_message": msg.strip()}) as span:
        # Add user message
        span.set_attribute("message", msg.strip())
        messages.append({"role": "user", "content": msg.strip()})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))
        await send(ChatInput())

        # Process with AI agent
        try:
            with tracer.start_as_current_span("ai_processing") as ai_span:
                ai_span.set_attribute("model", "gpt-4o-mini")
                ai_span.set_attribute("input_length", len(msg))

                result = await agent.run(msg)
                reply = result.response.text

                ai_span.set_attribute("output_length", len(reply))
                ai_span.set_attribute("success", True)

        except Exception as e:
            reply = f"Error: {e} (Check OPENAI_API_KEY environment variable)"
            span.set_attribute("error", True)
            span.set_attribute("error_message", str(e))

        messages.append({"role": "assistant", "content": reply})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))

@app.get("/test")
def test_traces():
    """Create some test traces for demonstration."""
    print("Creating test traces...")
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("operation", "test")
        span.set_attribute("user", "demo")

        # Simulate some work with nested spans
        with tracer.start_as_current_span("database_query") as db_span:
            db_span.set_attribute("query", "SELECT * FROM users")
            db_span.set_attribute("duration_ms", 45)

            # Simulate error in nested span
            with tracer.start_as_current_span("cache_lookup") as cache_span:
                cache_span.set_attribute("cache_key", "user:123")
                cache_span.set_attribute("hit", False)

        with tracer.start_as_current_span("response_formatting") as format_span:
            format_span.set_attribute("format", "json")
            format_span.set_attribute("size_bytes", 1024)

    return Div("Test traces created! Check the telemetry panel.", cls="alert alert-success")

@app.get("/")
def index():
    """Main page with telemetry demo."""
    with tracer.start_as_current_span("page_render") as span:
        span.set_attribute("page", "index")
        span.set_attribute("user_agent", "demo")

        return Title("FastHTML Opentelemetry Streamer"), Body(
            Div(
                H1("FastHTML Opentelemetry Streamer", cls="text-3xl font-bold text-center mb-8"),


                # Main content area
                Div(
                    # Left: Telemetry streaming
                    Div(
                        ft_otel.telemetry_container(),
                        cls="w-2/3 pr-4"
                    ),

                    # Right: Chat interface
                    Div(
                        H2("Agent Chat", cls="text-xl font-bold mb-4"),

                        Div(
                            *[ChatMessage(i) for i in range(len(messages))],
                            id="chatlist",
                            cls="h-[50vh] overflow-y-auto bg-base-200 p-4 rounded-lg mb-4"
                        ),

                        Form(
                            Group(ChatInput(), Button("Send", cls="btn btn-primary")),
                            hx_ext="ws",
                            ws_send=True,
                            ws_connect="/ws",
                            onsubmit="return false;",
                            cls="flex gap-2 mt-2"
                        ),

                        cls="w-1/3 pl-4"
                    ),

                    cls="flex gap-4"
                ),

                # Footer
                Div(
                    P(
                        "This demo shows real-time ",
                        A("OpenTelemetry", href="https://opentelemetry.io/", target="_blank", cls="underline"),
                        " streaming with ",
                        A("FastHTML", href="https://www.fastht.ml/", target="_blank", cls="underline"),
                        cls="text-center text-sm opacity-70 mt-8"
                    ),
                    P(
                        "It is built as part of the ",
                        A("Virtual Sea Trial Project (VST)", href="https://virtualseatrial.fi/", target="_blank", cls="underline"),
                        ", Funded by Business Finland",
                        cls="text-center text-sm opacity-70"
                    ),
                    P(
                        "Source code: ",
                        A("github.com/Novia-RDI-Seafaring/ft-otel", href="https://github.com/Novia-RDI-Seafaring/ft-otel", target="_blank", cls="underline"),
                        cls="text-center text-sm opacity-70"
                    ),
                    Details(
                        Summary("Citation", cls="text-center text-sm opacity-70 cursor-pointer mt-4"),
                        Pre(
                            """@software{fasthtml_otel,
  title={FastHTML OpenTelemetry Streamer},
  author={Christoffer Björkskog},
  year={2025},
  url={https://github.com/Novia-RDI-Seafaring/ft-otel}
}""",
                            cls="text-xs bg-base-200 p-2 rounded mt-2 overflow-x-auto"
                        ),
                        cls="mt-4"
                    ),
                    cls="mt-8"
                ),

                cls="container mx-auto px-4 py-8"
            )
        )

if __name__ == "__main__":
    import sys
    port = 8002
    if len(sys.argv) > 1 and sys.argv[1].startswith('--port='):
        port = int(sys.argv[1].split('=')[1])
    elif len(sys.argv) > 2 and sys.argv[1] == '--port':
        port = int(sys.argv[2])

    serve(host="0.0.0.0", port=port)