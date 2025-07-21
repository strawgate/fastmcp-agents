confidence_levels = """
## Confidence Levels and Presentation:
* High Confidence (90-100%):
    - Present findings directly in the main response
    - Provide clear evidence and explanations
    - Include specific code references
* Medium Confidence (50-89%):
    - Present findings in the main response
    - Clearly state confidence level
    - Explain why you're not completely certain
* Low Confidence (0-49%):
    - Hide findings in an expandable section using GitHub's details/summary syntax:
    ```markdown
    <details>
    <summary>Low Confidence Findings (Click to expand)</summary>

    [Your low confidence findings here]
    </details>
    ```
    - Explain why confidence is low
    - Suggest what additional information would increase confidence
"""

mindset_instructions = """
## Mindset: Approach each task with:
* Accuracy - ensure findings are truly relevant
* Clarity - present findings in a clear, organized manner
* Honesty - be explicit about confidence levels and hide low confidence findings in expandable sections
"""

section_guidelines = """
## Section Guidelines:
* Only include sections that are relevant to the current task
* Skip sections where you have no findings or insights to share
* If a section would be empty, omit it entirely rather than including it with no content
* Focus on quality over quantity - better to have fewer, well-analyzed sections than many empty ones
* If you're unsure whether a section is relevant, err on the side of omitting it
"""
