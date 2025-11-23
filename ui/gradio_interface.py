import gradio as gr
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import os

# Import core components
from ui.backend import DebugBackend, LocalBackend
from core.models import RankedSolution
from visualization.blaxel_generator import ErrorFlowVisualizer
from voice.elevenlabs_tts import VoiceExplainer
from config.api_keys import api_config

class DebugGenieUI:
    def __init__(self, backend: DebugBackend):
        self.backend = backend
        self.visualizer = ErrorFlowVisualizer()
        
        # Initialize voice explainer if API key is available
        try:
            self.voice_explainer = VoiceExplainer(api_key=api_config.elevenlabs_api_key)
        except:
            logger.warning("ElevenLabs API key not found - voice features disabled")
            self.voice_explainer = None
        
    async def handle_analyze(
        self, 
        error_text: str, 
        screenshot, 
        codebase_files,
        progress=gr.Progress()
    ):
        """Main analysis handler with progressive updates."""
        try:
            # Initialize outputs
            chat_history = []
            solutions_html = ""
            viz_html = ""
            voice_audio = None
            analysis_json = {}
            
            # Validate inputs
            if not error_text and screenshot is None:
                return (
                    [["❌ Error", "Please provide either an error message or a screenshot."]],
                    "<div>No analysis performed.</div>",
                    "<div>No visualization available.</div>",
                    None,
                    {},
                    "Status: ❌ Missing input"
                )
            
            progress(0.1, desc="Starting analysis...")
            chat_history.append({"role": "user", "content": f"Analyze this error:\n```\n{error_text[:200]}...\n```"})
            
            # Build context
            context = {
                'error_text': error_text,
                'image': screenshot,
                'code_context': ""
            }
            
            # Add screenshot context if provided
            if screenshot is not None:
                context['type'] = 'ide'  # Could be auto-detected
                
            progress(0.2, desc="Running multi-agent analysis...")
            
            # Run backend analysis
            result = await self.backend.analyze(context)
            
            progress(0.7, desc="Generating visualizations...")
            
            # Build chat response
            response_text = f"""
## 🎯 Root Cause
{result.root_cause}

## ✅ Recommended Solutions
"""
            for idx, sol in enumerate(result.solutions[:3], 1):
                response_text += f"\n### {idx}. {sol.get('title', 'Solution')}\n"
                response_text += f"{sol.get('description', '')}\n"
                response_text += f"**Confidence:** {sol.get('probability', 0):.0%}\n"
            
            chat_history.append({"role": "assistant", "content": response_text})
            
            # Generate solutions accordion HTML
            solutions_html = self._generate_solutions_html(result.solutions)
            
            # Generate 3D visualization if we have stack trace
            # For demo, create a mock trace
            mock_trace = self.visualizer.generate_mock_trace()
            viz_html = self.visualizer.generate_flow(mock_trace)
            
            # Build analysis JSON
            analysis_json = {
                "execution_time": f"{result.execution_time:.2f}s",
                "confidence": result.confidence_score,
                "agents_used": list(result.agent_metrics.keys()),
                "metrics": result.agent_metrics
            }
            
            # Generate voice explanation for top solution
            progress(0.9, desc="Generating voice explanation...")
            if self.voice_explainer and result.solutions:
                try:
                    # Convert first solution to RankedSolution format
                    top_solution = result.solutions[0]
                    ranked_sol = RankedSolution(
                        rank=1,
                        title=top_solution.get('title', 'Solution'),
                        description=top_solution.get('description', ''),
                        steps=[], # Would parse from fix_instructions
                        confidence=top_solution.get('probability', 0.5),
                        sources=[],
                        why_ranked_here=f"Top ranked solution with {top_solution.get('probability', 0)*100:.0f}% confidence",
                        trade_offs=[]
                    )
                    
                    audio_bytes = self.voice_explainer.generate_explanation(
                        ranked_sol, 
                        mode="walkthrough"
                    )
                    
                    if audio_bytes:
                        # Save to temp file for Gradio
                        voice_path = self.voice_explainer.save_audio(
                            audio_bytes, 
                            f"explanation_{hash(error_text[:100])}.mp3"
                        )
                        voice_audio = voice_path
                except Exception as e:
                    logger.warning(f"Voice generation failed: {e}")
                    voice_audio = None
            
            progress(1.0, desc="Complete!")
            
            return (
                chat_history,
                solutions_html,
                viz_html,
                voice_audio,
                analysis_json,
                f"Status: ✅ Analysis complete in {result.execution_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return (
                [[f"❌ Error", f"Analysis failed: {str(e)}"]],
                f"<div class='error'>Error: {str(e)}</div>",
                "<div>Visualization unavailable</div>",
                None,
                {"error": str(e)},
                f"Status: ❌ Failed - {str(e)}"
            )
    
    def _generate_solutions_html(self, solutions: List[Dict]) -> str:
        """Generate HTML for solutions accordion."""
        if not solutions:
            return "<div>No solutions found.</div>"
        
        html = "<div style='font-family: sans-serif;'>"
        
        for idx, sol in enumerate(solutions, 1):
            title = sol.get('title', f'Solution {idx}')
            desc = sol.get('description', 'No description')
            prob = sol.get('probability', 0.5)
            
            # Color code by probability
            color = "green" if prob > 0.7 else "orange" if prob > 0.4 else "red"
            
            html += f"""
            <details style='border: 2px solid {color}; border-radius: 8px; padding: 16px; margin: 12px 0;'>
                <summary style='font-size: 18px; font-weight: bold; cursor: pointer;'>
                    {idx}. {title} 
                    <span style='color: {color}; float: right;'>
                        {prob:.0%} confidence
                    </span>
                </summary>
                <div style='margin-top: 12px; padding: 12px; background: #f5f5f5; border-radius: 4px;'>
                    <p>{desc}</p>
                </div>
            </details>
            """
        
        html += "</div>"
        return html

def create_interface(backend: DebugBackend):
    """Create the main Gradio interface."""
    ui = DebugGenieUI(backend)
    
    with gr.Blocks(
        title="DebugGenie 🧞",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="purple"
        ),
        css="""
        .gradio-container {
            font-family: 'Inter', sans-serif;
        }
        .error {
            color: red;
            padding: 16px;
            background: #fee;
            border-radius: 8px;
        }
        """
    ) as demo:
        
        gr.Markdown(
            """
            # 🧞 DebugGenie - AI Debugging Assistant
            ### Multi-Agent AI System for Intelligent Error Analysis
            
            Powered by Claude, Gemini, and GPT-4 working together to solve your bugs.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📝 Input")
                
                error_input = gr.Code(
                    label="Paste Error Message / Stack Trace",
                    language="python",
                    lines=10
                )
                
                screenshot_input = gr.Image(
                    label="Upload Screenshot (Optional)",
                    type="pil",
                    sources=["upload", "clipboard"]
                )
                
                codebase_files = gr.File(
                    label="Upload Codebase Files (Optional)",
                    file_count="multiple"
                )
                
                analyze_btn = gr.Button(
                    "🔍 Analyze Error",
                    variant="primary",
                    size="lg"
                )
                
                gr.Markdown(
                    """
                    ---
                    **Tips:**
                    - Paste complete error traces for best results
                    - Screenshots help with IDE or browser errors
                    - Upload related code files for deeper analysis
                    """
                )
            
            with gr.Column(scale=2):
                gr.Markdown("## 🎯 Results")
                
                status_text = gr.Markdown("**Status:** Ready to analyze")
                
                with gr.Tabs():
                    with gr.Tab("💬 Chat"):
                        chatbot = gr.Chatbot(
                            height=500,
                            type="messages",
                            avatar_images=(
                                None,
                                "https://em-content.zobj.net/thumbs/120/apple/354/genie_1f9de.png"
                            )
                        )
                    
                    with gr.Tab("🎯 Solutions"):
                        solutions_accordion = gr.HTML(
                            value="<div>No solutions yet. Analyze an error to get started.</div>"
                        )
                    
                    with gr.Tab("🎨 3D Error Flow"):
                        viz_3d = gr.HTML(
                            value="<div style='text-align: center; padding: 40px;'>Visualization will appear here after analysis.</div>"
                        )
                    
                    with gr.Tab("📊 Analysis Details"):
                        analysis_details = gr.JSON(
                            label="Detailed Metrics"
                        )
                
                # Voice explanation (collapsed by default)
                with gr.Accordion("🔊 Voice Explanation", open=False):
                    voice_output = gr.Audio(
                        label="AI-Generated Explanation",
                        autoplay=False
                    )
        
        # Examples
        gr.Examples(
            examples=[
                [
                    "Traceback (most recent call last):\n  File \"app.py\", line 42, in process_data\n    result = json.loads(data)\njson.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)",
                    None,
                    None
                ],
                [
                    "TypeError: 'NoneType' object is not subscriptable\n  File \"main.py\", line 15, in get_user\n    return users[user_id]['name']",
                    None,
                    None
                ]
            ],
            inputs=[error_input, screenshot_input, codebase_files],
            label="📚 Example Errors"
        )
        
        # Event handlers
        analyze_btn.click(
            fn=ui.handle_analyze,
            inputs=[error_input, screenshot_input, codebase_files],
            outputs=[
                chatbot, 
                solutions_accordion, 
                viz_3d, 
                voice_output, 
                analysis_details, 
                status_text
            ]
        )
    
    return demo

if __name__ == "__main__":
    # Default to local backend for direct execution
    backend = LocalBackend()
    demo = create_interface(backend)
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
