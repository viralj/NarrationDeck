# Text+ Preset Setup (Default: Fusion Title Template)

This guide explains how to create a Text+ preset that NarrationDeck can apply
by name.

## Option A (Default): Fusion Title Template (Effects Library)
1) Open Resolve and go to the **Edit** page.
2) Open the **Effects Library** and locate **Titles > Text+**.
3) Drag **Text+** onto a timeline.
4) Open the **Inspector** and set your preferred styling (font, size, color,
   drop shadow, etc.).
5) Right-click the Text+ clip in the timeline and choose **Save As Fusion Title**.
6) Name the preset (e.g., `NarrationDeck_TextPlus`).

The preset should now appear under **Effects Library > Titles** with the name
you provided. NarrationDeck will reference this name when creating captions.

## Option B (Optional): Power Bin Clip (Cross-Project Reuse)
1) Open the **Media Pool** and enable **Power Bins**.
2) Create a Text+ clip with your preferred styling.
3) Store it in a Power Bin for reuse across projects in the same database.

If you choose this option, we can add support later to pull from the Power Bin
instead of the Effects Library.
