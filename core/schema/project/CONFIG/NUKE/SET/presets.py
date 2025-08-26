import nuke

# DOT
nuke.setUserPreset("Dot", "hidden", {'selected': 'true', 'note_font_color': '0xffffffff', 'hide_input': 'true', 'note_font_size': '30', 'tile_color': '0xff0000ff'})

# SHUFFLE
nuke.setUserPreset("Shuffle", "shuffle_ALL0", {'blue': 'black', 'selected': 'true', 'label': 'ALL 0', 'green': 'black', 'alpha': 'black', 'red': 'black'})
nuke.setUserPreset("Shuffle", "shuffle_ALL1", {'blue': 'white', 'selected': 'true', 'label': 'ALL 1', 'green': 'white', 'alpha': 'white', 'red': 'white'})
nuke.setUserPreset("Shuffle", "shuffle_R", {'blue': 'red', 'selected': 'true', 'label': 'R', 'green': 'red', 'alpha': 'red', 'red': 'red'})
nuke.setUserPreset("Shuffle", "shuffle_G", {'blue': 'green', 'selected': 'true', 'label': 'G', 'green': 'green', 'alpha': 'green', 'red': 'green'})
nuke.setUserPreset("Shuffle", "shuffle_B", {'blue': 'blue', 'selected': 'true', 'label': 'B', 'green': 'blue', 'alpha': 'blue', 'red': 'blue'})

# EXPRESSION
nuke.setUserPreset("Expression", "alpha/Alpha1WhenIsNot0", {'expr3': 'a != 0? 1:0', 'label': 'a != 0? 1:0'})
nuke.setUserPreset("Expression", "difference/OutputDifferenceAlpha", {'expr3': 'r != 0 || g != 0 || b != 0 || a != 0 ? 1 : 0', 'label': 'r != 0 || g != 0 || b != 0 || a != 0 ? 1 : 0'})