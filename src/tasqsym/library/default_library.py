# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

path = "tasqsym.library."

"""
If your robot uses custom/alt skills, import default_library.library and edit fields.
String paths are used instead of instances so that information can be sent between remote machines.
"""

library = {

    "prepare": {
        "decoder": path + "prepare.prepare.PrepareDecoder",
        "src":     path + "prepare.prepare.Prepare",
        "src_configs": {"interruptible": True}
    },

    "navigation": {
        "decoder": path + "navigation.navigation.NavigationDecoder",
        "src":     path + "navigation.navigation.Navigation",
        "src_configs": {"interruptible": True, "timeout": 600.0}
    },

    "find": {
        "decoder": path + "find.find.FindDecoder",
        "src":     path + "find.find.Find"
    },

    "look": {
        "decoder": path + "look.look.LookDecoder",
        "src":     path + "look.look.Look",
        "src_configs": {"interruptible": True}
    },

    "grasp": {
        "decoder": path + "grasp.grasp.GraspDecoder",
        "src":     path + "grasp.grasp.Grasp",
        "src_configs": {"num_approach_segments": 1, "num_grasp_segments": 1, "interruptible": True}
    },

    "pick": {
        "decoder": path + "pick.pick.PickDecoder",
        "src":     path + "pick.pick.Pick",
        "src_configs": {"num_segments": 1}
    },

    "bring": {
        "decoder": path + "bring.bring.BringDecoder",
        "src":     path + "bring.bring.Bring",
        "src_configs": {"num_segments": 1, "interruptible": True}
    },

    "place": {
        "decoder": path + "place.place.PlaceDecoder",
        "src":     path + "place.place.Place",
        "src_configs": {"num_segments": 1}
    },

    "release": {
        "decoder": path + "release.release.ReleaseDecoder",
        "src":     path + "release.release.Release",
        "src_configs": {"num_release_segments": 1, "num_depart_segments": 1, "interruptible": True}
    },

}