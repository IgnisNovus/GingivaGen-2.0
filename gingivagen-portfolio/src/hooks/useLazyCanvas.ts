import { useRef, useState, useEffect } from 'react'

/**
 * Returns a ref and a boolean. The boolean becomes true once the
 * element is within `rootMargin` of the viewport and stays true
 * forever (so the Canvas is never unmounted once loaded).
 */
export function useLazyCanvas(rootMargin = '200px') {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [rootMargin])

  return { ref, visible }
}
