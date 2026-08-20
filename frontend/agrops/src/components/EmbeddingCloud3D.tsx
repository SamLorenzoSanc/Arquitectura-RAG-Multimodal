import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";

export type EmbeddingPoint = {
  id: string;
  label: string;
  document?: string;
  content?: string;
  has_embedding?: boolean;
  words?: number;
  color: string;
  x?: number;
  y?: number;
  z?: number;
};

type Props = {
  points: EmbeddingPoint[];
  selectedId: string | null;
  onSelect: (point: EmbeddingPoint | null) => void;
};

const CANARY_BLUE = "#0768A9";

function fileName(path?: string) {
  if (!path) return "Sin documento";
  return path.split(/[\\/]/).pop() ?? path;
}

function normalize(points: EmbeddingPoint[]) {
  if (!points.length) return [];
  const xs = points.map((p) => p.x ?? 0);
  const ys = points.map((p) => p.y ?? 0);
  const zs = points.map((p) => p.z ?? 0);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const minZ = Math.min(...zs);
  const maxZ = Math.max(...zs);
  const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 1e-6);
  const scale = 10 / span;
  return points.map((point) => ({
    ...point,
    x: ((point.x ?? 0) - (minX + maxX) / 2) * scale,
    y: ((point.y ?? 0) - (minY + maxY) / 2) * scale,
    z: ((point.z ?? 0) - (minZ + maxZ) / 2) * scale,
  }));
}

type DocMarker = {
  id: string;
  name: string;
  color: string;
  x: number;
  y: number;
  z: number;
  count: number;
};

function setCursor(value: string) {
  document.body.style.cursor = value;
}

export default function EmbeddingCloud3D({
  points,
  selectedId,
  onSelect,
}: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [hoveredDoc, setHoveredDoc] = useState<string | null>(null);
  const cloud = useMemo(() => normalize(points), [points]);

  const documents = useMemo(() => {
    const grouped = new Map<string, DocMarker>();
    for (const point of cloud) {
      const name = fileName(point.document || point.label);
      const prev = grouped.get(name);
      if (!prev) {
        grouped.set(name, {
          id: `doc:${name}`,
          name,
          color: point.color,
          x: point.x ?? 0,
          y: point.y ?? 0,
          z: point.z ?? 0,
          count: 1,
        });
        continue;
      }
      prev.x += point.x ?? 0;
      prev.y += point.y ?? 0;
      prev.z += point.z ?? 0;
      prev.count += 1;
    }
    return [...grouped.values()].map((doc) => ({
      ...doc,
      x: doc.x / doc.count,
      y: doc.y / doc.count,
      z: doc.z / doc.count,
    }));
  }, [cloud]);

  const selectedPoint = cloud.find((point) => point.id === selectedId) ?? null;
  const focusDoc =
    hoveredDoc ||
    (selectedPoint
      ? fileName(selectedPoint.document || selectedPoint.label)
      : null);
  const hoveredPoint = cloud.find((point) => point.id === hoveredId) ?? null;

  return (
    <Canvas
      camera={{ position: [0, 2.4, 16], fov: 50 }}
      gl={{ antialias: true }}
      onPointerMissed={() => onSelect(null)}
      className="touch-none"
    >
      <color attach="background" args={["#f8fafc"]} />
      <ambientLight intensity={0.85} />
      <directionalLight position={[8, 12, 6]} intensity={0.65} />
      <axesHelper args={[6]} />
      <gridHelper args={[24, 24, "#cbd5e1", "#e2e8f0"]} />

      {cloud.map((point) => {
        const docName = fileName(point.document || point.label);
        const focused = point.id === selectedId || point.id === hoveredId;
        const muted = Boolean(focusDoc) && docName !== focusDoc;
        return (
          <mesh
            key={point.id}
            position={[point.x ?? 0, point.y ?? 0, point.z ?? 0]}
            onClick={(event) => {
              event.stopPropagation();
              onSelect(point);
            }}
            onPointerOver={(event) => {
              event.stopPropagation();
              setHoveredId(point.id);
              setCursor("pointer");
            }}
            onPointerOut={() => {
              setHoveredId(null);
              setCursor("auto");
            }}
          >
            <sphereGeometry args={[focused ? 0.2 : 0.11, 16, 16]} />
            <meshStandardMaterial
              color={point.has_embedding === false ? "#94a3b8" : point.color}
              transparent
              opacity={muted ? 0.12 : 1}
              roughness={0.35}
            />
          </mesh>
        );
      })}

      {documents.map((doc) => {
        const muted = Boolean(focusDoc) && doc.name !== focusDoc;
        return (
          <mesh
            key={doc.id}
            position={[doc.x, doc.y, doc.z]}
            onClick={(event) => {
              event.stopPropagation();
              const first = cloud.find(
                (point) => fileName(point.document || point.label) === doc.name,
              );
              onSelect(first ?? null);
            }}
            onPointerOver={(event) => {
              event.stopPropagation();
              setHoveredDoc(doc.name);
              setCursor("pointer");
            }}
            onPointerOut={() => {
              setHoveredDoc(null);
              setCursor("auto");
            }}
          >
            <sphereGeometry args={[0.38, 24, 24]} />
            <meshStandardMaterial
              color={doc.color}
              wireframe
              transparent
              opacity={muted ? 0.12 : 0.7}
            />
            <Html
              center
              distanceFactor={16}
              style={{ pointerEvents: "none", whiteSpace: "nowrap" }}
            >
              <div className="rounded-md border border-slate-200 bg-white/95 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700 shadow-sm">
                {doc.name} · {doc.count}
              </div>
            </Html>
          </mesh>
        );
      })}

      {hoveredPoint && (
        <Html
          position={[
            hoveredPoint.x ?? 0,
            (hoveredPoint.y ?? 0) + 0.42,
            hoveredPoint.z ?? 0,
          ]}
          center
          style={{ pointerEvents: "none", whiteSpace: "nowrap" }}
        >
          <div className="max-w-[240px] truncate rounded-md bg-slate-900 px-2 py-1 text-[10px] text-white shadow">
            {fileName(hoveredPoint.document || hoveredPoint.label)}
          </div>
        </Html>
      )}

      <Html position={[0, -7.2, 0]} center style={{ pointerEvents: "none" }}>
        <p className="text-[11px] text-slate-500">
          UMAP 3D · color = documento · esfera grande = centroide ·{" "}
          <span style={{ color: CANARY_BLUE }}>arrastra para orbitar</span>
        </p>
      </Html>

      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={4}
        maxDistance={40}
      />
    </Canvas>
  );
}
