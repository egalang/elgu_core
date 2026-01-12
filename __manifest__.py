# -*- coding: utf-8 -*-
{
    "name": "eLGU Core",
    "version": "19.0.1.0.0",
    "category": "Government",
    "summary": "Core request/workflow engine for eLGU Online Citizen Services",
    "depends": [
        "base",
        "mail",
        "account",
    ],
    "data": [
        "security/elgu_security.xml",
        "security/ir.model.access.csv",
        "data/elgu_sequence.xml",
        "data/elgu_seed_config.xml",
        "views/elgu_request_stage_views.xml",
        "views/elgu_request_type_views.xml",
        "views/elgu_requirement_views.xml",
        "views/elgu_request_views.xml",
        "views/elgu_menus.xml",
    ],
    "demo": [
        "demo/elgu_demo_partners.xml",
        "demo/elgu_demo_requests.xml",
    ],
    "license": "LGPL-3",
    "application": True,
    "installable": True,
}
