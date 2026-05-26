FEATURE_BAN_TYPES = [
    'forums',
    'tickets',
    'messaging',
    'wiki_edit',
    'buying_buses',
    'selling_buses',
    'creating_liveries',
    'creating_vehicles',
    'creating_games',
    'creating_operators',
    'deleting_operators',
    'mass_add_vehicles',
    'mass_edit_vehicles',
    'reporting',
    'groups',
    'giveaways',
    'tracking',
    'live_maps',
    'community_hub',
]

FEATURE_BAN_ALIASES = {
    'forum': 'forums',
    'ticket': 'tickets',
    'wiki_editing': 'wiki_edit',
}

FEATURE_BAN_PATH_RULES = {
    'creating_liveries': ('/create/livery/',),
    'creating_vehicles': ('/create/vehicle/',),
    'creating_games': ('/create/game/',),
    'creating_operators': ('/operator/create/',),
    'reporting': ('/report/',),
    'groups': ('/group/create/',),
    'giveaways': ('/giveaway/enter/',),
    'tracking': ('/tracking/',),
    'live_maps': ('/map/',),
    'community_hub': ('/hub/',),
}

FEATURE_BAN_REGEX_RULES = {
    'deleting_operators': (r'^/operator/[^/]+/delete/$',),
    'mass_add_vehicles': (r'^/operator/[^/]+/vehicles/mass-add-bus/$',),
    'mass_edit_vehicles': (
        r'^/operator/[^/]+/vehicles/mass-edit-bus/$',
        r'^/operator/[^/]+/vehicles/select-mass-edit-bus/$',
    ),
}
