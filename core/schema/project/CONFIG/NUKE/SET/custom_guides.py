import guides
import os

viewer_guides = [
  guides.Guide("title safe", 1, 1, 1, 0.1, guides.kGuideMasked),
  guides.Guide("action safe", 1, 1, 1, 0.05, guides.kGuideMasked),
  guides.FormatCenterGuide("format center", 1, 1, 1, 0.1, guides.kGuideSequence),
  guides.Guide("Format", 1, 0, 0, 0, guides.kGuideSequence),
]

project_mask = os.environ["PROJECTMASK"]
string_mask = project_mask + ":1"
float_mask = float(project_mask)
viewer_masks = [
  guides.MaskGuide("16:9", 16.0/9.0),
  guides.MaskGuide("14:9", 14.0/9.0),
  guides.MaskGuide("1.66:1", 1.66),
  guides.MaskGuide("1.85:1", 1.85),
  guides.MaskGuide("2.35:1", 2.35),
  guides.MaskGuide("2.2:1",2.2/1.0),
guides.MaskGuide(string_mask, float_mask/1.0),
guides.MaskGuide("2:1", 2.0/1.0),
]
