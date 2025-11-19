from typing import List, Dict, Any, Optional
import json
from pydantic import BaseModel
from loguru import logger

# Mocking Blaxel SDK for now as it's a hypothetical or external dependency not in requirements
# In a real scenario, we would import: from blaxel import Scene, Node, Edge, Animation
# We will generate a Plotly 3D scatter plot as a fallback/implementation of the concept
import plotly.graph_objects as go

class StackFrame(BaseModel):
    function: str
    file: str
    line: int
    is_external: bool = False

class ErrorFlowVisualizer:
    def __init__(self):
        pass

    def _get_node_color(self, idx: int, total: int, is_external: bool) -> str:
        if is_external:
            return "purple"
        if idx == 0:
            return "green" # Entry
        if idx == total - 1:
            return "red" # Error
        return "blue" # Normal

    def generate_flow(self, stack_trace: List[Dict[str, Any]]) -> str:
        """
        Generate 3D visualization of error flow.
        Returns HTML string of the visualization.
        """
        try:
            frames = [StackFrame(**f) for f in stack_trace]
            if not frames:
                return "<div>No stack trace available for visualization.</div>"

            # Limit nodes for performance
            if len(frames) > 50:
                frames = frames[-50:]

            # 3D Coordinates layout (simple spiral or linear)
            x_coords = []
            y_coords = []
            z_coords = []
            colors = []
            sizes = []
            hover_texts = []
            
            for idx, frame in enumerate(frames):
                # Simple linear layout along X axis, with slight spiral
                x_coords.append(idx * 2)
                y_coords.append(0) 
                z_coords.append(0)
                
                color = self._get_node_color(idx, len(frames), frame.is_external)
                colors.append(color)
                
                # Pulse effect for error node (simulated by larger size)
                size = 20 if idx == len(frames) - 1 else 12
                sizes.append(size)
                
                hover_texts.append(
                    f"<b>{frame.function}</b><br>"
                    f"{frame.file}:{frame.line}<br>"
                    f"{'External Library' if frame.is_external else 'User Code'}"
                )

            # Create Nodes Trace
            node_trace = go.Scatter3d(
                x=x_coords, y=y_coords, z=z_coords,
                mode='markers+text',
                marker=dict(
                    size=sizes,
                    color=colors,
                    opacity=0.8,
                    line=dict(width=2, color='white')
                ),
                text=[f.function for f in frames],
                textposition="top center",
                hoverinfo='text',
                hovertext=hover_texts
            )

            # Create Edges Trace
            edge_x = []
            edge_y = []
            edge_z = []
            
            for i in range(len(frames) - 1):
                edge_x.extend([x_coords[i], x_coords[i+1], None])
                edge_y.extend([y_coords[i], y_coords[i+1], None])
                edge_z.extend([z_coords[i], z_coords[i+1], None])

            edge_trace = go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='#888', width=2),
                hoverinfo='none'
            )

            # Layout
            layout = go.Layout(
                title="3D Error Flow Visualization",
                showlegend=False,
                scene=dict(
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    zaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    bgcolor='rgba(0,0,0,0)'
                ),
                margin=dict(l=0, r=0, b=0, t=30),
                height=500
            )

            fig = go.Figure(data=[edge_trace, node_trace], layout=layout)
            
            # Return HTML div
            return fig.to_html(full_html=False, include_plotlyjs='cdn')

        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            return f"<div>Error generating visualization: {str(e)}</div>"

    def generate_mock_trace(self) -> List[Dict[str, Any]]:
        """Generate a mock trace for testing."""
        return [
            {"function": "main", "file": "app.py", "line": 10, "is_external": False},
            {"function": "process_request", "file": "core/handler.py", "line": 45, "is_external": False},
            {"function": "validate_input", "file": "utils/validation.py", "line": 12, "is_external": False},
            {"function": "json.loads", "file": "json/decoder.py", "line": 337, "is_external": True},
            {"function": "decode", "file": "json/decoder.py", "line": 355, "is_external": True},
        ]
