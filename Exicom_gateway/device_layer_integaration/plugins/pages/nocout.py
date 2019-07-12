"""Apache page handler for nocout Device App web-services
"""

import nocout
import bulk_setconfig

pagehandlers.update({
    "nocout": nocout.main,
    "bulk_setconfig": bulk_setconfig.live_setconfig
})
