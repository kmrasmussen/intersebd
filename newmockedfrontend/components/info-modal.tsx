"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { HelpCircle } from "lucide-react"

interface InfoModalProps {
  title: string
  description: string
  triggerClassName?: string
}

export function InfoModal({ title, description, triggerClassName = "" }: InfoModalProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className={`inline-flex items-center justify-center text-gray-500 hover:text-gray-700 focus:outline-none ${triggerClassName}`}
        aria-label={`Information about ${title}`}
      >
        <HelpCircle className="h-4 w-4" />
      </button>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription className="pt-2 text-base text-gray-700 whitespace-pre-wrap">
              {description}
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </>
  )
}
