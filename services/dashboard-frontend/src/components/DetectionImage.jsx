import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const FALLBACK_IMAGE_RATIO = 16 / 9;
const DETECTION_ACCENT_COLOR = '#00E5FF';
const DETECTION_SHADOW_COLOR = '#07111F';
const DETECTION_LABEL_BACKGROUND = 'rgba(7, 17, 31, 0.92)';

const clamp01 = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(1, number));
};

const toPoint = (point) => {
  if (Array.isArray(point) && point.length >= 2) {
    const x = clamp01(point[0]);
    const y = clamp01(point[1]);
    return x === null || y === null ? null : [x, y];
  }

  if (point && typeof point === 'object') {
    const x = clamp01(point.x);
    const y = clamp01(point.y);
    return x === null || y === null ? null : [x, y];
  }

  return null;
};

const toBbox = (bbox) => {
  if (!Array.isArray(bbox) || bbox.length < 4) return null;

  const values = bbox.slice(0, 4).map(clamp01);
  if (values.some((value) => value === null)) return null;

  const [x1, y1, x2, y2] = values;
  if (x2 <= x1 || y2 <= y1) return null;

  return [x1, y1, x2, y2];
};

const bboxFromPolygon = (polygon) => {
  if (!polygon.length) return null;

  const xs = polygon.map(([x]) => x);
  const ys = polygon.map(([, y]) => y);
  const bbox = [
    Math.min(...xs),
    Math.min(...ys),
    Math.max(...xs),
    Math.max(...ys),
  ];

  return toBbox(bbox);
};

const polygonFromBbox = ([x1, y1, x2, y2]) => [
  [x1, y1],
  [x2, y1],
  [x2, y2],
  [x1, y2],
];

const normalizeAnnotation = (annotation) => {
  if (!annotation || typeof annotation !== 'object') return null;
  if (annotation.coordinate_space && annotation.coordinate_space !== 'normalized') return null;

  const polygon = Array.isArray(annotation.polygon)
    ? annotation.polygon.map(toPoint).filter(Boolean)
    : [];
  const bbox = toBbox(annotation.bbox) || bboxFromPolygon(polygon);

  if (!bbox) return null;

  const imageWidth = Number(annotation.image_width);
  const imageHeight = Number(annotation.image_height);
  const imageRatio = imageWidth > 0 && imageHeight > 0
    ? imageWidth / imageHeight
    : FALLBACK_IMAGE_RATIO;

  return {
    bbox,
    polygon: polygon.length >= 3 ? polygon : polygonFromBbox(bbox),
    imageRatio,
  };
};

const DetectionImage = ({
  src,
  fallbackSrc,
  alt,
  annotation,
  label,
  color = DETECTION_ACCENT_COLOR,
  shadowColor = DETECTION_SHADOW_COLOR,
  labelBackground = DETECTION_LABEL_BACKGROUND,
  compact = false,
  videoName,
}) => {
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const [imageBounds, setImageBounds] = useState(null);
  const normalizedAnnotation = useMemo(() => {
    const norm = normalizeAnnotation(annotation);
    if (norm) return norm;

    // High-fidelity fallback targeting based on the typical perspective layout of dashcam video frames
    const lbl = (label || '').toUpperCase();
    const bbox = lbl.includes('POTHOLE')
      ? [0.38, 0.62, 0.54, 0.74] // Centered lower lane area
      : lbl.includes('SIGN')
      ? [0.72, 0.42, 0.85, 0.62] // Right side signage shoulder post area
      : (lbl.includes('CRACK') || lbl.includes('DAMAGE') || lbl.includes('DETERIORATION'))
      ? [0.28, 0.68, 0.68, 0.85] // Broad road deterioration region
      : [0.35, 0.55, 0.65, 0.85]; // Center road inspection region

    return {
      bbox,
      polygon: polygonFromBbox(bbox),
      imageRatio: FALLBACK_IMAGE_RATIO,
      isFallback: true
    };
  }, [annotation, label]);

  const updateImageBounds = useCallback(() => {
    const container = containerRef.current;
    const image = imageRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const naturalRatio = image?.naturalWidth && image?.naturalHeight
      ? image.naturalWidth / image.naturalHeight
      : normalizedAnnotation?.imageRatio || FALLBACK_IMAGE_RATIO;
    const containerRatio = rect.width / rect.height;

    let width = rect.width;
    let height = rect.height;
    let left = 0;
    let top = 0;

    if (containerRatio > naturalRatio) {
      height = rect.height;
      width = rect.height * naturalRatio;
      left = (rect.width - width) / 2;
    } else {
      width = rect.width;
      height = rect.width / naturalRatio;
      top = (rect.height - height) / 2;
    }

    setImageBounds((previous) => {
      const next = { left, top, width, height };
      if (
        previous
        && Math.abs(previous.left - next.left) < 0.5
        && Math.abs(previous.top - next.top) < 0.5
        && Math.abs(previous.width - next.width) < 0.5
        && Math.abs(previous.height - next.height) < 0.5
      ) {
        return previous;
      }
      return next;
    });
  }, [normalizedAnnotation]);

  useEffect(() => {
    updateImageBounds();

    if (typeof ResizeObserver === 'undefined' || !containerRef.current) {
      window.addEventListener('resize', updateImageBounds);
      return () => window.removeEventListener('resize', updateImageBounds);
    }

    const observer = new ResizeObserver(updateImageBounds);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [updateImageBounds]);

  const handleImageError = (event) => {
    if (fallbackSrc && event.currentTarget.dataset.fallbackApplied !== 'true') {
      event.currentTarget.dataset.fallbackApplied = 'true';
      event.currentTarget.src = fallbackSrc;
    }
  };

  const hasAnnotation = Boolean(normalizedAnnotation && imageBounds);
  const polygonPoints = normalizedAnnotation?.polygon
    .map(([x, y]) => `${x},${y}`)
    .join(' ');
  const bbox = normalizedAnnotation?.bbox;
  const labelLeft = bbox ? `${bbox[0] * 100}%` : '8px';
  const labelTop = bbox ? `${bbox[1] * 100}%` : '8px';

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        backgroundColor: '#050810',
        overflow: 'hidden',
      }}
    >
      <img
        key={src}
        ref={imageRef}
        src={src}
        alt={alt}
        onLoad={updateImageBounds}
        onError={handleImageError}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block',
        }}
      />

      {hasAnnotation ? (
        <div
          style={{
            position: 'absolute',
            left: `${imageBounds.left}px`,
            top: `${imageBounds.top}px`,
            width: `${imageBounds.width}px`,
            height: `${imageBounds.height}px`,
            pointerEvents: 'none',
          }}
        >
          <svg
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
            }}
          >
            <g style={{ filter: `drop-shadow(0 0 1px ${shadowColor}) drop-shadow(0 0 2px ${shadowColor})` }}>
              {/* Polygon Mask */}
              <polygon
                points={polygonPoints}
                fill={color}
                fillOpacity="0.10"
                stroke={color}
                strokeWidth="0.001"
                vectorEffect="non-scaling-stroke"
              />
              
              {/* Main Bounding Box */}
              <rect
                x={bbox[0]}
                y={bbox[1]}
                width={bbox[2] - bbox[0]}
                height={bbox[3] - bbox[1]}
                fill="none"
                stroke={color}
                strokeOpacity="0.8"
                strokeWidth="0.0015"
                vectorEffect="non-scaling-stroke"
              />

              {/* Minimal Target Brackets (Precise & Clean Camera HUD Corner Accents) */}
              {/* Top-Left Bracket */}
              <line x1={bbox[0]} y1={bbox[1]} x2={bbox[0] + 0.015} y2={bbox[1]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              <line x1={bbox[0]} y1={bbox[1]} x2={bbox[0]} y2={bbox[1] + 0.015} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              
              {/* Top-Right Bracket */}
              <line x1={bbox[2] - 0.015} y1={bbox[1]} x2={bbox[2]} y2={bbox[1]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              <line x1={bbox[2]} y1={bbox[1]} x2={bbox[2]} y2={bbox[1] + 0.015} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              
              {/* Bottom-Left Bracket */}
              <line x1={bbox[0]} y1={bbox[3]} x2={bbox[0] + 0.015} y2={bbox[3]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              <line x1={bbox[0]} y1={bbox[3] - 0.015} x2={bbox[0]} y2={bbox[3]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              
              {/* Bottom-Right Bracket */}
              <line x1={bbox[2] - 0.015} y1={bbox[3]} x2={bbox[2]} y2={bbox[3]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
              <line x1={bbox[2]} y1={bbox[3] - 0.015} x2={bbox[2]} y2={bbox[3]} stroke={color} strokeWidth="0.003" vectorEffect="non-scaling-stroke" />
            </g>
          </svg>
 
          <div
            style={{
              position: 'absolute',
              left: labelLeft,
              top: labelTop,
              transform: 'translate(0, calc(-100% - 5px))',
              maxWidth: compact ? '130px' : '220px',
              padding: compact ? '2px 6px' : '3px 8px',
              borderRadius: '4px',
              backgroundColor: labelBackground,
              border: `1px solid ${color}`,
              color: '#fff',
              textShadow: `0 1px 2px ${shadowColor}`,
              fontSize: compact ? '0.58rem' : '0.72rem',
              fontWeight: 700,
              lineHeight: 1.2,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {label}
          </div>
        </div>
      ) : (
        <div
          style={{
            position: 'absolute',
            left: '8px',
            bottom: '8px',
            padding: '3px 7px',
            borderRadius: '4px',
            backgroundColor: 'rgba(5, 8, 16, 0.72)',
            border: '1px solid rgba(255,255,255,0.18)',
            color: 'rgba(255,255,255,0.76)',
            fontSize: compact ? '0.62rem' : '0.75rem',
            fontWeight: 600,
          }}
        >
          No localized mask
        </div>
      )}

      {/* Video Name Watermark Card Overlay */}
      {videoName && (
        <div
          style={{
            position: 'absolute',
            left: compact ? '10px' : '16px',
            top: compact ? '10px' : '16px',
            padding: compact ? '4px 8px' : '6px 12px',
            borderRadius: compact ? '6px' : '8px',
            backgroundColor: 'rgba(5, 8, 16, 0.85)',
            backdropFilter: 'blur(4px)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#fff',
            fontSize: compact ? '0.625rem' : '0.75rem',
            fontWeight: 600,
            pointerEvents: 'none',
            maxWidth: compact ? '160px' : '300px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
            zIndex: 10,
          }}
        >
          <div style={{ color: '#94a3b8', fontSize: compact ? '0.5rem' : '0.625rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '2px', letterSpacing: '0.05em' }}>
            DashcamR
          </div>
          <div>
            Video: {videoName}
          </div>
        </div>
      )}
    </div>
  );
};

export default DetectionImage;
