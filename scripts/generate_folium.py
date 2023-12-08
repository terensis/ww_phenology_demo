"""
Generate a folium map of the data in the data directory to
visualize the results of the phenology model in a HTML file.

Author: Lukas Graf (lukas.graf@terensis.io)
"""

import folium
import geopandas as gpd

from branca.element import Element, MacroElement, Template
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


def get_textbox_css():
    return """
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
            <pre>
            Die Karte zeigt das Auflaufdatum (BBCH 09) und das Datum
            des Ende des Ährenschiebens (BBCH 59) in Winterweizen.
            Die Phänologiedaten beruhen auf einer Simulation mit
            hochaufgelösten Wetterdaten von MeteoSchweiz.</pre>
        </div>
        </div>
        <div style="position: fixed; 
                top: 10px; 
                left: 50px; 
                width: 250px; 
                height: 80px; 
                z-index:9999; 
                font-size:14px;
                text-align: center;">
        <img src="https://github.com/terensis/ww_phenology_demo/raw/main/resources/terensis_logo.png" alt="Terensis" style="width: 250px; height: auto;">
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
        font-size: 14px;
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
    .textbox .textbox-content {
        color: black;
        text-align: left;
        margin-bottom: 5px;
        font-size: 14px;
        }
    </style>
    {% endmacro %}
    """


def generate_folium_map(
    data_dir: Path,
    output_dir: Path,
    output_name: str = 'index.html',
    selected_years: list[int] = [2018, 2019, 2020]
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

    # Add custom Terensis style
    textbox_css = get_textbox_css()
    my_custom_style = MacroElement()
    my_custom_style._template = Template(textbox_css)
    # Adding to the map
    m.get_root().add_child(my_custom_style)
    
    # add data
    idx = 0
    for fpath in data_dir.glob('*.geojson'):
        year = int(fpath.stem.split('_')[-1].split('-')[-1])
        if year not in selected_years:
            continue

        gdf = gpd.read_file(fpath)
        gdf_indexed = gdf.set_index('id')

        # emergence date
        show = idx == 0
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
            legend_name=f'Beginn des Auflaufens {year} (Tag des Jahres)',
            show=show
        )
        # add a tooltip to display the emergence date as date
        for s in emergence.geojson.data['features']:
            s['properties']['Auflaufen (BBCH 09)'] = \
                gdf_indexed.loc[
                    int(s['id']), 'Auflaufen (BBCH 09)']
        # and finally adding a tooltip/hover to the choropleth's geojson
        folium.GeoJsonTooltip(['Auflaufen (BBCH 09)']).add_to(
            emergence.geojson)

        # handle colormap
        for key in emergence._children:
            if key.startswith('color_map'):
                branca_color_map = emergence._children[key]
                del(emergence._children[key])

        m.add_child(emergence)
        m.add_child(branca_color_map)
        m.add_child(BindColormap(emergence, branca_color_map))       

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
            legend_name=f'Ende des Ährenschiebens {year} (Tag des Jahres)',
            show=False
        )
        # add a tooltip to display the heading date as date
        for s in heading.geojson.data['features']:
            s['properties']['Ende des Aehrenschieben (BBCH 59)'] = \
                gdf_indexed.loc[
                    int(s['id']), 'Ende des Aehrenschieben (BBCH 59)']

        # and finally adding a tooltip/hover to the choropleth's geojson
        folium.GeoJsonTooltip(['Ende des Aehrenschieben (BBCH 59)']).add_to(
            heading.geojson)

        # handle colormap
        for key in heading._children:
            if key.startswith('color_map'):
                branca_color_map = heading._children[key]
                del(heading._children[key])

        m.add_child(heading)
        m.add_child(branca_color_map)
        m.add_child(BindColormap(heading, branca_color_map))

        idx += 1

    # save map
    m.add_child(folium.map.LayerControl(collapsed=False))
    m.save(output_dir.joinpath(output_name))


if __name__ == '__main__':
    data_dir = Path('data')
    output_dir = Path('.')
    output_dir.mkdir(exist_ok=True)
    generate_folium_map(data_dir, output_dir)
