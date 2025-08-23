'use client'

import { ReactNode } from 'react'

interface SmoothScrollLinkProps {
  href: string
  children: ReactNode
  className?: string
  offset?: number
}

export default function SmoothScrollLink({ 
  href, 
  children, 
  className, 
  offset = 16 
}: SmoothScrollLinkProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault()
    
    const targetId = href.replace('#', '')
    const targetElement = document.getElementById(targetId)
    
    if (targetElement) {
      const elementPosition = targetElement.getBoundingClientRect().top
      const offsetPosition = elementPosition + window.pageYOffset - offset
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      })
      
      // 确保焦点管理
      setTimeout(() => {
        targetElement.focus({ preventScroll: true })
      }, 500)
    }
  }

  return (
    <a
      href={href}
      onClick={handleClick}
      className={className}
    >
      {children}
    </a>
  )
}
