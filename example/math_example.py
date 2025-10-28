"""Mathematical reasoning example with step-by-step problem solving."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Resource
from pydantic_ai import Agent
import datetime
from pydantic import BaseModel
from typing import Tuple, Literal

# Set up telemetry
resource = Resource.create({"service.name": "Math Reasoning Demo"})
provider = TracerProvider(resource=resource)

from fasthtml.common import *
import sys
sys.path.insert(0, '..')

import fasthtml_otel as ft_otel
from math_renderer import MathRenderer

# Create FastHTML app
app = FastHTML(exts="ws")
streamer = ft_otel.configure(
    app,
    provider,
    renderers=[MathRenderer()]
)

# Instrument Pydantic AI
ft_otel.instrument_pydantic_ai(provider)

tracer = provider.get_tracer("Math Reasoning Demo")

# The agent will use individual tools for calculations rather than structured schemas
class CalculationResponse(BaseModel):
    result: float
    variable_name: str = ""
# Create mathematical reasoning agent
math_agent = Agent(
    "gpt-4o-mini",
    output_type=CalculationResponse,
    system_prompt="""You are a mathematical reasoning assistant that solves problems step by step using tools to calculate mathematical operations."""
)

# Individual mathematical tools will create their own traces
from pydantic import BaseModel

from typing import Literal
MathOperation = Literal["addition", "subtraction", "multiplication", "division", "square_root", "cube_root", "power", "logarithm", "exponential"]
Operand = Tuple[str, float]

class CalculationRequest(BaseModel):
    short_text: str
    variable_name: str = ""
    formula: MathOperation
    a: Operand
    b: Operand


@math_agent.tool_plain()
def calculate(motivation:str, x_name: str, a_name: str, a_value: float, b_name: str, b_value: float, operation  : MathOperation) -> CalculationResponse:
    """Calculate a mathematical operation. themotivation is onyl text, and very short"""
    with tracer.start_as_current_span(motivation) as span:
        span.set_attribute("math.operation", operation)
        result:float = 0
        formula = ""
        if operation == "addition":
            result:float = a_value + b_value
            formula:str = f"{x_name} = {a_name} + {b_name}"
        elif operation == "subtraction":
            result:float = a_value - b_value
            formula = f"{x_name} = {a_name} - {b_name}"
        elif operation == "multiplication":
            result:float = a_value * b_value    
            formula = f"{x_name} = {a_name} * {b_name}"
        elif operation == "division":
            result:float = a_value / b_value
            formula = f"{x_name} = {a_name} / {b_name}"
        elif operation == "square_root":
            result:float = math.sqrt(a_value)
            formula = f"{x_name} = √{a_name}"
        elif operation == "cube_root":
            result:float = math.cbrt(a_value)
            formula = f"{x_name} = ∛{a_name}"
        elif operation == "power":
            result:float = a_value ** b_value
            formula = f"{x_name} = {a_name} ^ {b_name}"
        span.set_attribute("math.formula", formula)
        span.set_attribute("math.result", f"{x_name} = {result}")
        return CalculationResponse(result=result, variable_name=x_name)
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
        placeholder="Ask me a math question... (e.g., 'Solve x² - 5x + 6 = 0')",
        cls="input input-bordered w-full",
        hx_swap_oob="true",
    )

# Individual mathematical tools will create their own traces

@app.ws("/ws")
async def math_chat_socket(msg: str, send):
    """Handle math chat WebSocket messages."""
    print(f"Math question: {msg}")

    with tracer.start_as_current_span(
        "Math Problem Solving Session",
        attributes={"math.problem": msg.strip()}
    ) as main_span:
        # Add user message
        messages.append({"role": "user", "content": msg.strip()})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))
        await send(ChatInput())

        try:
            result = await math_agent.run(
                f"Solve this math problem step by step using the available mathematical tools: {msg}"
            )
            print(result)

            reply_text = result.response.text if hasattr(result.response, 'text') else str(result.response)


        except Exception as e:
            reply = f"Error solving math problem: {e}"
            main_span.set_attribute("error", True)
            main_span.set_attribute("error_message", str(e))

        messages.append({"role": "assistant", "content": reply_text})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))

@app.get("/")
def index():
    """Main page with math reasoning demo."""
    with tracer.start_as_current_span("page_render") as span:
        span.set_attribute("page", "math_reasoning")

        return Title("Mathematical Reasoning Demo"), Body(
            Div(
                H1("Mathematical Reasoning with Live Traces", cls="text-3xl font-bold text-center mb-8"),

                # Main content area
                Div(
                    # Left: Mathematical traces (like a math paper)
                    Div(
                        ft_otel.telemetry_container(
                            title="📊 Mathematical Solution Steps",
                            cls="h-[70vh] overflow-y-auto p-4 bg-base-100 rounded-lg border"
                        ),
                        cls="w-2/3 pr-4"
                    ),

                    # Right: Math problem interface
                    Div(
                        H2("🧮 Ask a Math Question", cls="text-xl font-bold mb-4"),

                        Div(
                            *[ChatMessage(i) for i in range(len(messages))],
                            id="chatlist",
                            cls="h-[40vh] overflow-y-auto bg-base-200 p-4 rounded-lg mb-4"
                        ),

                        Form(
                            Group(ChatInput(), Button("Solve", cls="btn btn-primary")),
                            hx_ext="ws",
                            ws_send=True,
                            ws_connect="/ws",
                            onsubmit="return false;",
                            cls="flex gap-2 mb-4"
                        ),

                        # Sample problems
                        Div(
                            H3("Sample Problems:", cls="font-medium mb-2"),
                            Button("x² - 5x + 6 = 0", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Solve x² - 5x + 6 = 0'"),
                            Button("2x + 5 = 13", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Solve 2x + 5 = 13'"),
                            Button("Add 15 + 27", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Add 15 + 27'"),
                            Button("Calculate 8 × 6", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Calculate 8 × 6'"),
                            Button("Find √64", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Find the square root of 64'"),
                            Button("3² + 4²", cls="btn btn-outline btn-sm mr-2 mb-2",
                                   onclick="document.getElementById('msg-input').value='Calculate 3² + 4²'"),
                            cls="mb-4"
                        ),

                        
                        cls="w-1/3 pl-4"
                    ),

                    cls="flex gap-4"
                ),

                # Footer
                Div(
                    P("This demo shows mathematical reasoning with step-by-step traces displayed like a math paper.",
                      cls="text-center text-sm opacity-70 mt-8"),
                    P("Built with FastHTML + OpenTelemetry streaming",
                      cls="text-center text-sm opacity-70"),
                    cls="mt-8"
                ),

                cls="container mx-auto px-4 py-8"
            ),
            # Custom CSS for math styling
            Style("""
                .math-step {
                    page-break-inside: avoid;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
            """)
        )

if __name__ == "__main__":
    import sys
    port = 8003
    if len(sys.argv) > 1 and sys.argv[1].startswith('--port='):
        port = int(sys.argv[1].split('=')[1])
    elif len(sys.argv) > 2 and sys.argv[1] == '--port':
        port = int(sys.argv[2])

    serve(host="0.0.0.0", port=port)