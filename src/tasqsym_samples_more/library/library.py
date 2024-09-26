# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# --------------------------------------------------------------------------------------------

path = "tasqsym_samples_more.library."

library = {

    "action": {
        "decoder": path + "node.node.NodeDecoder",
        "src":     path + "node.node.Node",
        "src_configs": {"interruptible": True}
    },

}