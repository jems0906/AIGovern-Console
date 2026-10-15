import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

export default function Dialog({ title, children, onClose, wide = false }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialog = ref.current
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return <dialog ref={ref} className={wide ? 'wide' : ''} onCancel={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose() }} aria-labelledby="dialog-title"><header><h2 id="dialog-title">{title}</h2><button className="icon-button" title="Close" aria-label="Close" onClick={onClose}><X size={20} /></button></header>{children}</dialog>
}