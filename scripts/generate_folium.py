"""
Generate a folium map of the data in the data directory to
visualize the results of the phenology model in a HTML file.

Author: Lukas Graf (lukas.graf@terensis.io)
"""

import folium
import geopandas as gpd

from branca.element import Template, MacroElement
from pathlib import Path


class BindColormap(MacroElement):
    """Binds a colormap to a given layer.

    Parameters
    ----------
    colormap : branca.colormap.ColorMap
        The colormap to bind.
    """
    def __init__(self, layer, colormap):
        super(BindColormap, self).__init__()
        self.layer = layer
        self.colormap = colormap
        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
            {{this._parent.get_name()}}.on('overlayadd', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
                }});
            {{this._parent.get_name()}}.on('overlayremove', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'none';
                }});
        {% endmacro %}
        """)  # noqa


def generate_folium_map(
    data_dir: Path,
    output_dir: Path,
    output_name: str = 'ww_phenology_ch.html',
    selected_years: list[int] = [2016]
) -> None:
    """
    Generate a folium map of the data in the data directory to
    visualize the results of the phenology model in a HTML file.

    :param data_dir: directory with the data (geojson files).
    :param output_dir: directory for writing outputs to.
    :param output_name: name of the output file.
    :param selected_years: list of years to select.
    """
    # create map
    m = folium.Map(
        location=[47, 7.5],
        zoom_start=8,
        tiles='cartodbpositron',
        attr='© Terensis (2023). Basemap data © CartoDB'
    )

    # Injecting custom css through branca macro elements and template, give it a name
    textbox_css = """
    {% macro html(this, kwargs) %}
    <!doctype html>
    <html lang="de">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Phänologie Demo Terensis</title>
        <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.1/css/all.min.css" integrity="sha512-MV7K8+y+gLIBoVD59lQIYicR65iaqukzvf/nwasF0nqhPay5w/9lJmVM2hMDcnK1OnMGCdVK+iQrJ7lzPJQd1w==" crossorigin="anonymous" referrerpolicy="no-referrer"/>
        <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
        <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>

        <script>
        $( function() {
            $( "#textbox" ).draggable({
            start: function (event, ui) {
                $(this).css({
                right: "auto",
                top: "auto",
                bottom: "auto"
                });
            }
            });
        });
        </script>
    </head>

    <body>
        <div id="textbox" class="textbox">
        <div class="textbox-title">Winterweizen Phänologie</div>
        <div class="textbox-content">
            <p>Die Karte zeigt das Auflaufdatum (BBCH 09) und das Datum des Ende des Ährenschiebens (BBCH 59) in Winterweizen.</p>
            <p>Die Phänologiedaten beruhen auf einer Simulation mit hochaufgelösten Wetterdaten von MeteoSchweiz.</p>
        </div>
        </div>
    </body>
    </html>

    <style type='text/css'>
    .textbox {
        position: absolute;
        z-index:9999;
        border-radius:4px;
        background: rgba( 90, 114, 71, 0.25 );
        box-shadow: 0 8px 32px 0 rgba( 90, 114, 71, 0.37 );
        backdrop-filter: blur( 4px );
        -webkit-backdrop-filter: blur( 4px );
        border: 4px solid rgba( 90, 114, 71, 0.2 );
        padding: 10px;
        font-size:14px;
        right: 20px;
        bottom: 20px;
        color: #5a7247;
    }
    .textbox .textbox-title {
        color: black;
        text-align: center;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 22px;
        }
    </style>
    {% endmacro %}
    """
    # configuring the custom style (you can call it whatever you want)
    my_custom_style = MacroElement()
    my_custom_style._template = Template(textbox_css)
    # Adding my_custom_style to the map
    m.get_root().add_child(my_custom_style)

    # add data
    for fpath in data_dir.glob('*.geojson'):
        year = int(fpath.stem.split('_')[-1].split('-')[-1])
        if year not in selected_years:
            continue

        gdf = gpd.read_file(fpath)
        gdf_indexed = gdf.set_index('id')

        # emergence date
        emergence = folium.Choropleth(
            geo_data=gdf,
            name=f'{year} Auflaufen',
            data=gdf,
            columns=['id', 'emergence_date:doy'],
            key_on='feature.properties.id',
            fill_color='viridis',
            fill_opacity=0.7,
            line_opacity=0.2,
            lazy=True,
            legend_name='Beginn des Auflaufens (Tag des Jahres)'
        ).add_to(m)
        # add a tooltip to display the emergence date as date
        for s in emergence.geojson.data['features']:
            s['properties']['Auflaufen (BBCH 09)'] = \
                gdf_indexed.loc[
                    int(s['id']), 'Auflaufen (BBCH 09)']
        # and finally adding a tooltip/hover to the choropleth's geojson
        folium.GeoJsonTooltip(['Auflaufen (BBCH 09)']).add_to(
            emergence.geojson)

        # heading date
        heading = folium.Choropleth(
            geo_data=gdf,
            name=f'{year} Ährenschieben',
            data=gdf,
            columns=['id', 'heading_date:doy'],
            key_on='feature.properties.id',
            fill_color='viridis',
            fill_opacity=0.7,
            line_opacity=0.2,
            lazy=True,
            legend_name='Ende des Ährenschiebens (Tag des Jahres)',
            visible=False
        ).add_to(m)
        # add a tooltip to display the heading date as date
        for s in heading.geojson.data['features']:
            s['properties']['Ende des Aehrenschieben (BBCH 59)'] = \
                gdf_indexed.loc[
                    int(s['id']), 'Ende des Aehrenschieben (BBCH 59)']

        # and finally adding a tooltip/hover to the choropleth's geojson
        folium.GeoJsonTooltip(['Ende des Aehrenschieben (BBCH 59)']).add_to(
            heading.geojson)

    # add layer control
    folium.LayerControl().add_to(m)
    # save map
    m.save(output_dir.joinpath(output_name))


if __name__ == '__main__':
    data_dir = Path('data')
    output_dir = Path('map')
    output_dir.mkdir(exist_ok=True)
    generate_folium_map(data_dir, output_dir)
