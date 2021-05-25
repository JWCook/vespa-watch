# Overview Vespa-Watch user types

## Management

These users only have access to the management page.

- Rights: `Active`
- No extra rights are selected

## Management + personal info

These users have access to the management page and can also access the admin section to check the data on individuals, nests and nests management actions.

- Rights: `Active` + `Staff`
- The following extra rights are selected:
    ```
    Auth/recht/can view permission
    Contenttypes/inhoudstype/can view content type
    database/constance/can view constance
    vespawatch/individual/ can view individual
    vespawatch/magagement action/can view management action
    vespawatch/nest/can view nest

## Superusers

These users have full access and the rights to change, remove and delete items. They can also create new accounts.

- Rights: `Active` + `Staff` + `Superusers`
- No extra rights are selected
