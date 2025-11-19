from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Any
from collections import defaultdict
import ast
from pathlib import Path
from loguru import logger

@dataclass
class ExecutionNode:
    function_name: str
    file: str
    line: int
    children: List['ExecutionNode'] = field(default_factory=list)
    is_error: bool = False
    depth: int = 0
    call_count: int = 1  # For detecting recursion
    
    def __hash__(self):
        return hash((self.function_name, self.file, self.line))

class FlowAnalyzer:
    def __init__(self):
        self.visited_nodes: Set[tuple] = set()
        self.recursion_threshold = 3  # Max times to visit same node
        
    def analyze_flow(self, stack_trace: List[Dict[str, Any]]) -> Optional[ExecutionNode]:
        """
        Analyze execution flow from stack trace.
        Builds a tree representing the call hierarchy.
        """
        if not stack_trace:
            return None
            
        try:
            # Build tree from stack trace (stack trace is usually bottom-up)
            # Reverse it to get top-down execution flow
            frames = list(reversed(stack_trace))
            
            root = None
            prev_node = None
            
            for idx, frame in enumerate(frames):
                node = ExecutionNode(
                    function_name=frame.get('function', 'unknown'),
                    file=frame.get('file', 'unknown'),
                    line=frame.get('line', 0),
                    is_error=(idx == len(frames) - 1),  # Last frame is error
                    depth=idx
                )
                
                # Check for recursion
                node_key = (node.function_name, node.file)
                if node_key in self.visited_nodes:
                    # Potential recursion detected
                    node.call_count = sum(1 for n in self._get_all_nodes([root]) if 
                                         n and n.function_name == node.function_name)
                    
                self.visited_nodes.add(node_key)
                
                if idx == 0:
                    root = node
                else:
                    if prev_node:
                        prev_node.children.append(node)
                        
                prev_node = node
                
            return root
            
        except Exception as e:
            logger.error(f"Flow analysis failed: {e}")
            return None
    
    def find_divergence_points(self, flow: ExecutionNode) -> List[Dict[str, Any]]:
        """
        Find where execution could have gone differently.
        Analyzes conditional branches and exception handlers.
        """
        divergence_points = []
        
        if not flow:
            return divergence_points
            
        # Traverse the flow tree
        nodes = self._get_all_nodes([flow])
        
        for node in nodes:
            if not node:
                continue
                
            # Try to read the source file and look for conditionals
            try:
                file_path = Path(node.file)
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                        
                    # Parse AST to find conditionals near this line
                    tree = ast.parse(source)
                    divergences = self._find_conditionals_near_line(tree, node.line)
                    
                    for div in divergences:
                        divergence_points.append({
                            'file': node.file,
                            'function': node.function_name,
                            'line': div['line'],
                            'type': div['type'],
                            'description': div['description']
                        })
                        
            except Exception as e:
                logger.debug(f"Could not analyze divergence in {node.file}: {e}")
                continue
                
        return divergence_points
    
    def detect_infinite_recursion(self, flow: ExecutionNode) -> Dict[str, Any]:
        """
        Detect potential infinite recursion patterns.
        """
        if not flow:
            return {'detected': False}
            
        # Count function call frequencies
        call_counts = defaultdict(int)
        nodes = self._get_all_nodes([flow])
        
        for node in nodes:
            if node:
                call_counts[node.function_name] += 1
                
        # Check for suspicious patterns
        max_calls = max(call_counts.values()) if call_counts else 0
        
        if max_calls >= self.recursion_threshold:
            culprit = [name for name, count in call_counts.items() 
                      if count >= self.recursion_threshold]
            return {
                'detected': True,
                'functions': culprit,
                'max_depth': max_calls,
                'warning': f"Potential infinite recursion in: {', '.join(culprit)}"
            }
            
        return {'detected': False}
    
    def get_critical_path(self, flow: ExecutionNode) -> List[ExecutionNode]:
        """
        Get the main execution path (the path to the error).
        """
        if not flow:
            return []
            
        path = []
        current = flow
        
        while current:
            path.append(current)
            if current.is_error:
                break
            # Follow first child (main path)
            current = current.children[0] if current.children else None
            
        return path
    
    def build_call_graph(self, flow: ExecutionNode) -> Dict[str, List[str]]:
        """
        Build a directed graph representation of function calls.
        Returns adjacency list.
        """
        graph = defaultdict(list)
        
        if not flow:
            return dict(graph)
            
        nodes = self._get_all_nodes([flow])
        
        for node in nodes:
            if node and node.children:
                for child in node.children:
                    if child:
                        graph[node.function_name].append(child.function_name)
                        
        return dict(graph)
    
    def _get_all_nodes(self, nodes: List[ExecutionNode]) -> List[ExecutionNode]:
        """Recursively collect all nodes in the tree."""
        result = []
        for node in nodes:
            if node:
                result.append(node)
                result.extend(self._get_all_nodes(node.children))
        return result
    
    def _find_conditionals_near_line(self, tree: ast.AST, target_line: int, 
                                    window: int = 5) -> List[Dict[str, Any]]:
        """
        Find conditional statements near a specific line.
        """
        conditionals = []
        
        for node in ast.walk(tree):
            if hasattr(node, 'lineno'):
                line_no = node.lineno
                
                # Check if within window
                if abs(line_no - target_line) <= window:
                    if isinstance(node, ast.If):
                        conditionals.append({
                            'line': line_no,
                            'type': 'if',
                            'description': 'Conditional branch'
                        })
                    elif isinstance(node, ast.Try):
                        conditionals.append({
                            'line': line_no,
                            'type': 'try',
                            'description': 'Exception handler'
                        })
                    elif isinstance(node, ast.For) or isinstance(node, ast.While):
                        conditionals.append({
                            'line': line_no,
                            'type': 'loop',
                            'description': 'Loop structure'
                        })
                        
        return conditionals
    
    def generate_flow_summary(self, flow: ExecutionNode) -> Dict[str, Any]:
        """Generate a comprehensive summary of the execution flow."""
        if not flow:
            return {'error': 'No flow data'}
            
        nodes = self._get_all_nodes([flow])
        critical_path = self.get_critical_path(flow)
        recursion_info = self.detect_infinite_recursion(flow)
        divergence_points = self.find_divergence_points(flow)
        
        return {
            'total_calls': len(nodes),
            'depth': max(n.depth for n in nodes if n),
            'critical_path_length': len(critical_path),
            'recursion_detected': recursion_info['detected'],
            'recursion_details': recursion_info,
            'divergence_points': len(divergence_points),
            'call_graph': self.build_call_graph(flow)
        }
