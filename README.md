# Vespa-watch

Django app for the monitoring and management of [_Vespa velutina_](https://www.inaturalist.org/taxa/119019-Vespa-velutina), an invasive species in Belgium.

## Installation

### Setup database

1. Create an empty PostgreSQL database (e.g. `vespa-watch`)
2. Enable PostGIS: `CREATE EXTENSION postgis;`

### Define settings

1. Clone this repository: `git clone https://github.com/inbo/vespa-watch`
2. Copy [`djangoproject/settings/settings_local.template.py`](djangoproject/settings/settings_local.template.py) to `djangoproject/settings/settings_local.py`
3. In that file, verify the database settings are correct and set `SECRET_KEY` to a non-empty value

### Setup python environment

1. Create a virtual environment, e.g. `conda create -n vespawatch python=3.6`
2. Activate the environment, e.g. `source activate vespawatch`
3. Navigate to the project directory and install the requirements: `pip install -r requirements.txt`
4. Tell Django to use the local settings: `export DJANGO_SETTINGS_MODULE=djangoproject.settings.settings_local`

### Apply database migrations

```bash
python manage.py migrate
```

### Create superuser

* In development (this will prompt for a username, email and password):

    ```bash
    python manage.py createsuperuser
    ```

* In production:

    ```
    python manage.py create_su
    ```

### Create fire brigade users

1. Fire brigade users are responsible for a specific geographic area (= zone). Import the polygons for those zones:

    ```bash
    python manage.py import_firefighters_zones data/Brandweerzones_2019.geojson
    ```

    <details>
    <summary>File source</summary>

    The initial fire brigade zone data was received as an ESRI shapefile and converted to GeoJSON with:

    ```bash
    ogr2ogr -f GeoJSON -t_srs EPSG:4326 data/Brandweerzones_2019.geojson <path_to_received_shapefile>/Brandweerzones_2019.shp
    ```
    </details>

2. Create a fire brigade user for each zone (this will return passwords for each account, so best to catch those):

    ```bash
    python manage.py create_firefighters_accounts
    ```

### Load data from iNaturalist

Initialize the database with observations from iNaturalist (optional):

```bash
python manage.py sync_pull
```

## Run the application

In your virtual environment:

```bash
python manage.py runserver
```

Go to http://localhost:8000 to see the application.

## Development

### Update HTML

HTML is defined in [templates](https://docs.djangoproject.com/en/2.1/topics/templates/) at [`vespawatch/templates/vespawatch`](vespawatch/templates/vespawatch). `base.html` is the main template, almost all other templates build upon it. The HTML is structured around [Bootstrap v4.0](https://getbootstrap.com/docs/4.0/getting-started/introduction/) classes for layout, components and utilities: use these before writing custom html and css.

### Node package manager (npm) for CSS and Javascript

CSS & JS are managed in [`static_src`](static_src). **Important**: files in the Django accessible directory [`vespawatch/static/vespawatch`](vespawatch/static/vespawatch) should not be edited manually, but compiled or copied with Node Package Manager. To start:

1. Verify [npm](https://www.npmjs.com/get-npm) is installed: `node -v`
2. Go to the root of this repository
2. Install all dependencies with: `npm install` (will read [`package.json`](package.json) to create the `node_modules` directory)

### Update CSS

CSS is managed as SCSS in [`static_src/scss`](static_src/scss). The SCSS starts from Bootstrap's SCSS, with custom variable overwrites in `_variables.scss` and custom CSS in `main.scss`. These get bundled together with Bootstrap in a single `vespawatch/static/vespawatch/css/main.css`.

1. Go to the [`static_src/scss`](static_src/scss)
2. Update the relevant `.scss` files
3. Generate the CSS automatically on every change with `npm run watch:css` (or once with `npm run create:css`).

### Update JS libraries

External JS libraries (and their CSS) are defined in [`package.json`](package.json). To add a library:

1. In [`package.json`](package.json) under `dependencies` add the library and version
2. Install the library with `npm install`
3. In `package.json` under `scripts` create a new script to move the necessary JS & CSS files to `vespawatch/static/vespawatch/libraries` (see the other scripts for inspiration) and add your script to `copy:libraries`
4. Move the files with `npm run copy:libraries`
5. Link to the files in your template with:
    ```html
    <link rel="stylesheet" href="{% static 'vespawatch/libraries/my_library/my_library.min.css' %}">
    <script src="{% static 'vespawatch/libraries/my_library/my_library.min.js' %}"></script>
    ```

## Contributors

[List of contributors](https://github.com/inbo/vespa-watch/contributors)

## License

[MIT License](https://github.com/inbo/vespa-watch/blob/master/LICENSE)
