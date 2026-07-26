'use client';

export default function EntityGraph({ graph, onNodeSelected }) {
  if (!graph) return <div className="empty">Select a case to load its relationship graph.</div>;
  const nodes = graph.nodes.slice(0, 16);
  const centre = { x: 430, y: 220 };
  const positions = Object.fromEntries(nodes.map((node, index) => {
    const angle = Math.PI * 2 * index / nodes.length - Math.PI / 2;
    const radius = index ? 130 + (index % 3) * 34 : 0;
    return [node.id, { x: centre.x + Math.cos(angle) * radius, y: centre.y + Math.sin(angle) * radius }];
  }));
  const colours = { case: '#6f95ff', vehicle: '#a49aff', person: '#63d5bd', evidence: '#ffb36d' };
  return <svg viewBox="0 0 860 440" className="graph-svg" role="img" aria-label="Case entity relationship graph">
    <g className="edges">{graph.edges.filter(e => positions[e.source] && positions[e.target]).map((edge, index) => <g key={`${edge.source}-${edge.target}-${index}`}><line x1={positions[edge.source].x} y1={positions[edge.source].y} x2={positions[edge.target].x} y2={positions[edge.target].y} /><text x={(positions[edge.source].x + positions[edge.target].x) / 2} y={(positions[edge.source].y + positions[edge.target].y) / 2}>{edge.label}</text></g>)}</g>
    <g>{nodes.map((node) => <g key={node.id} className="graph-node" onClick={() => onNodeSelected?.(node)}><circle cx={positions[node.id].x} cy={positions[node.id].y} r={node.type === 'case' ? 32 : 25} stroke={colours[node.type] || '#aab8cb'} strokeWidth={Math.max(1.5, node.confidence * 3)} /><text x={positions[node.id].x} y={positions[node.id].y - 2}>{node.label.slice(0, 16)}</text><text className="node-type" x={positions[node.id].x} y={positions[node.id].y + 12}>{node.type}</text></g>)}</g>
  </svg>;
}
