import { useEffect, useRef } from "react";

export default function StarField({ active = true }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);

  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const STAR_COUNT = 280;
    const stars = Array.from({ length: STAR_COUNT }, () => {
      const tier = Math.random();
      const size =
        tier < 0.7
          ? Math.random() * 0.6 + 0.3
          : tier < 0.95
          ? Math.random() * 0.7 + 0.9
          : Math.random() * 0.9 + 1.6;
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 0.18 + 0.06;
      return {
        x: Math.random() * (canvas.width || window.innerWidth),
        y: Math.random() * (canvas.height || window.innerHeight),
        size,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        opacity: Math.random() * 0.5 + 0.45,
        opacityDelta: (Math.random() * 0.012 + 0.004) * (Math.random() < 0.5 ? 1 : -1),
      };
    });

    const draw = () => {
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      for (const s of stars) {
        s.x += s.vx;
        s.y += s.vy;
        if (s.x < -2) s.x = W + 2;
        if (s.x > W + 2) s.x = -2;
        if (s.y < -2) s.y = H + 2;
        if (s.y > H + 2) s.y = -2;

        s.opacity += s.opacityDelta;
        if (s.opacity >= 0.95 || s.opacity <= 0.25) s.opacityDelta *= -1;

        if (s.size >= 1.4) {
          const g = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.size * 2.5);
          g.addColorStop(0, `rgba(255,255,255,${(s.opacity * 0.7).toFixed(3)})`);
          g.addColorStop(1, "rgba(255,255,255,0)");
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.size * 2.5, 0, Math.PI * 2);
          ctx.fillStyle = g;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${s.opacity.toFixed(3)})`;
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener("resize", resize);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [active]);

  if (!active) return null;

  return (
    <canvas
      ref={canvasRef}
      style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", display: "block" }}
      aria-hidden="true"
    />
  );
}
