import React from 'react'
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DialogProps {
  children: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

interface DialogTriggerProps {
  children: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

interface DialogContentProps {
  className?: string
  children: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

interface DialogHeaderProps {
  className?: string
  [key: string]: any
}

interface DialogFooterProps {
  className?: string
  [key: string]: any
}

interface DialogTitleProps {
  className?: string
  [key: string]: any
}

interface DialogDescriptionProps {
  className?: string
  [key: string]: any
}

// Simple Dialog implementation to avoid Radix UI complexity
const Dialog: React.FC<DialogProps> = ({ children, open, onOpenChange }) => {
  return (
    <>
      {React.Children.map(children, child =>
        React.isValidElement(child) ? React.cloneElement(child, { open, onOpenChange }) : child
      )}
    </>
  )
}

const DialogTrigger: React.FC<DialogTriggerProps> = ({ children, open, onOpenChange }) => {
  return (
    <div onClick={() => onOpenChange?.(true)}>
      {children}
    </div>
  )
}

const DialogContent: React.FC<DialogContentProps> = ({ className, children, open, onOpenChange }) => {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/80"
        onClick={() => onOpenChange?.(false)}
      />
      
      {/* Content */}
      <div className={cn(
        "relative z-50 grid w-full max-w-lg gap-4 border bg-white p-6 shadow-lg sm:rounded-lg",
        className
      )}>
        {children}
        <button
          onClick={() => onOpenChange?.(false)}
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </button>
      </div>
    </div>
  )
}

const DialogHeader: React.FC<DialogHeaderProps> = ({ className, ...props }) => (
  <div
    className={cn(
      "flex flex-col space-y-1.5 text-center sm:text-left",
      className
    )}
    {...props}
  />
)

const DialogFooter: React.FC<DialogFooterProps> = ({ className, ...props }) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
)

const DialogTitle: React.FC<DialogTitleProps> = ({ className, ...props }) => (
  <h2
    className={cn(
      "text-lg font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
)

const DialogDescription: React.FC<DialogDescriptionProps> = ({ className, ...props }) => (
  <p
    className={cn("text-sm text-gray-600", className)}
    {...props}
  />
)

export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
}