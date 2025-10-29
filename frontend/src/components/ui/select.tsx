import React, { useState, useRef, useEffect } from "react"
import { ChevronDown, Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface SelectProps {
  children: React.ReactNode
  value?: string
  onValueChange?: (value: string) => void
  className?: string
  id?: string
  [key: string]: any
}

// Simple Select implementation without Radix UI
const Select: React.FC<SelectProps> = ({ children, value, onValueChange, ...props }) => {
  const [isOpen, setIsOpen] = useState<boolean>(false)
  const [selectedValue, setSelectedValue] = useState<string>(value || '')
  const selectRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setSelectedValue(value || '')
  }, [value])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (selectRef.current && !selectRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={selectRef} className="relative" {...props}>
      {React.Children.map(children, child =>
        React.isValidElement(child) 
          ? React.cloneElement(child, { 
              isOpen, 
              setIsOpen, 
              selectedValue, 
              setSelectedValue, 
              onValueChange 
            })
          : child
      )}
    </div>
  )
}

const SelectTrigger = ({ className, children, isOpen, setIsOpen, ...props }) => (
  <button
    type="button"
    className={cn(
      "flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-background placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    onClick={() => setIsOpen(!isOpen)}
    {...props}
  >
    {children}
    <ChevronDown className={cn("h-4 w-4 opacity-50 transition-transform", isOpen && "rotate-180")} />
  </button>
)

const SelectValue = ({ placeholder, selectedValue, children }) => {
  return (
    <span className={cn("truncate", !selectedValue && "text-gray-500")}>
      {selectedValue ? children : placeholder || "Select..."}
    </span>
  )
}

const SelectContent = ({ className, children, isOpen, selectedValue, setSelectedValue, onValueChange, setIsOpen }) => {
  if (!isOpen) return null

  return (
    <div className={cn(
      "absolute top-full left-0 z-50 mt-1 w-full max-h-96 overflow-auto rounded-md border bg-white shadow-lg",
      className
    )}>
      <div className="p-1">
        {React.Children.map(children, child =>
          React.isValidElement(child) 
            ? React.cloneElement(child, { 
                selectedValue, 
                setSelectedValue, 
                onValueChange, 
                setIsOpen 
              })
            : child
        )}
      </div>
    </div>
  )
}

const SelectItem = ({ className, children, value, selectedValue, setSelectedValue, onValueChange, setIsOpen, ...props }) => {
  const isSelected = selectedValue === value

  const handleClick = () => {
    setSelectedValue(value)
    onValueChange?.(value)
    setIsOpen(false)
  }

  return (
    <div
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-gray-100 focus:bg-gray-100",
        isSelected && "bg-blue-50 text-blue-900",
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {isSelected && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <Check className="h-4 w-4" />
        </span>
      )}
      {children}
    </div>
  )
}

// Simplified components for compatibility
const SelectGroup = ({ children }) => <div>{children}</div>
const SelectLabel = ({ className, ...props }) => (
  <div className={cn("py-1.5 pl-8 pr-2 text-sm font-semibold text-gray-500", className)} {...props} />
)
const SelectSeparator = ({ className, ...props }) => (
  <div className={cn("-mx-1 my-1 h-px bg-gray-200", className)} {...props} />
)

export { Select }