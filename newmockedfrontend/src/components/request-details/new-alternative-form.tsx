"use client"

import { Button } from "@/components/ui/button"; // Corrected path

type NewAlternativeFormProps = {
  newAlternative: string
  setNewAlternative: (value: string) => void
}

export function NewAlternativeForm({ newAlternative, setNewAlternative }: NewAlternativeFormProps) {
  const handleSubmit = () => {
    // In a real application, this would make an API call to submit the new alternative
    console.log("Submit new alternative:", newAlternative)
    setNewAlternative("")
  }

  return (
    <div>
      <h3 className="font-medium mb-2">Submit New Alternative:</h3>
      <div className="flex gap-2">
        <textarea
          className="flex-1 p-2 border rounded-md min-h-[100px]"
          placeholder="Enter a better completion here..."
          value={newAlternative}
          onChange={(e) => setNewAlternative(e.target.value)}
        />
        <div className="flex flex-col justify-end">
          <Button variant="outline" className="whitespace-nowrap" onClick={handleSubmit}>
            Submit New Alternative
          </Button>
        </div>
      </div>
    </div>
  )
}
