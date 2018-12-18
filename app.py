"""
Simple interface for downloading ACS data from the Census API,
primarily for internal customers working on consulting projects.

Created by Caleb Courtney
"""
# built-in libraries
import urllib.parse

# external libraries
import pandas as pd
import flask
import requests

# plotly-specific external libraries
import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table_experiments as dt


def get_acs_table(acsVariable, regionLevel, concept, year):
    """Downloads the specific table from the ACS API

    Args:
        acsVariable (str): Comma-separated string of the acs datasets
        regionLevel (str): ACS region type to use (us, state, county, etc)
        concept (str): The ACS Group (aka concept) selected by the user. used for renaming columns to friendly output
        year (str): string

    Returns:
        pandas.DataFrame: pd Dataframe of properly formatted data
    """
    censusKey = ''
    # build the url
    url = 'https://api.census.gov/data/%s/acs/acs5?get=NAME,%s&for=%s:*&key=%s' % (year, acsVariable, regionLevel, censusKey)
    # get the data
    df = pd.read_json(url)

    new_header = df.iloc[0]  # grab the first row for the header
    df = df[1:]  # take the data less the header row
    df.columns = new_header  # set the header row as the df header

    # we need to define the column order, so it's easier for the user to read
    # first the region column comes first
    column_order = []
    for column in ['us', 'state', 'county', 'metropolitan statistical area/micropolitan statistical area', 'zip code tabulation area']:
        if column in df.columns:
            column_order.append(column)

    # then we add the name of the region
    column_order.append('NAME')

    # then we add the data columns, in sorted order
    data_columns = []
    for column in df.columns:
        if column not in column_order:
            data_columns.append(column)

    data_columns.sort()
    for column in data_columns:
        column_order.append(column)

    # reorder the columns
    df = df[column_order]

    # using the group selected by the user, we can rename the columns to be more user-friendly
    groups_data = requests.get("https://api.census.gov/data/%s/acs/acs5/groups/%s.json" % (year, concept)).json()
    variablesData = {}
    for key, value in groups_data['variables'].items():
        variablesData[key] = value['label']

    df.rename(columns = variablesData, inplace = True)

    # now that we have the text, let's remove some of the uglier portions of the ACS syntax
    for column in df.columns:
        newColumnName = column.replace('Estimate!!', '')
        newColumnName = newColumnName.replace('Total!!', '')
        newColumnName = newColumnName.replace('!!', ': ')
        df.rename(columns = {column: newColumnName}, inplace = True)

    return df


# dash is really just flask under-the-hood with some helpful interface elements for javascript
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server)
app.config['suppress_callback_exceptions'] = True

# these are currently the only geography options that are supported
# adding other geog options is possible, but architecturally difficult
geographyOptions = [
    {
        'label': 'United States',
        'value': 'us'
    },
    {
        'label': 'State',
        'value': 'state'
    },
    {
        'label': 'Metro/Micro-politan Area',
        'value': 'metropolitan%20statistical%20area/micropolitan%20statistical%20area'
    },
    {
        'label': 'County',
        'value': 'county'
    },
    {
        'label': 'ZIP',
        'value': 'zip%20code%20tabulation%20area'
    }
]

# this will need to be update every year when the new 5-year ACS data comes out
year_options = [{'label': str(x), 'value': str(x)} for x in range(2010, 2018)]

# this is the layout of the app, as dash defines it. it's basically a bunch of html
app.layout = html.Div([
    html.Div([
        html.Label('ACS year (5-year Survey)'),
        dcc.Dropdown(
            id = 'acs-year',
            options = year_options,
            value = '2017'
        ),
        html.Label('ACS Concept'),
        dcc.Dropdown(
            id = 'acs-concept',
            options = [],
            value= 'B01001',
        ),
        html.Label('ACS Variable'),
        dcc.Dropdown(id = 'acs-variable', value='B01001_001E', multi=True),
        html.Label('Geography Level'),
        dcc.Dropdown(id = 'region-level', value = 'us', options = geographyOptions)
    ]
    ),
    html.Div(),
    dcc.Markdown("### Data Results\n*Please note that data from Puerto Rico is included in national totals."),
    html.Div(id = 'acs-table'),
    dcc.Markdown('###  '),
    html.A(
        html.Button('Download Data'),
        id = 'download-link',
        download="rawdata.csv",
        target="_blank"
    ),
    html.Div(dt.DataTable(rows=[{}]), style={'display': 'none'})
],
    className='container'
)


@app.callback(
    dash.dependencies.Output('acs-concept', 'options'),
    [
        dash.dependencies.Input('acs-year', 'value')
    ]
)
def set_concept_options(year):
    """Given an input year by the user, we look for what ACS Groups are availabl.

    Args:
        year (str): The year chosen by the user, in string format

    Returns:
        list: returns a list of dict options with 'label' and 'value' as keys. see how `year_options` is formatted above
    """
    groups_url = 'https://api.census.gov/data/%s/acs/acs5/groups.json' % year
    groups_data = requests.get(groups_url).json()['groups']
    concepts = []
    for group in groups_data:
        concepts.append(
            {
                'label': group['description'].lower().title(),
                'value': group['name']
            }
        )

    return concepts


@app.callback(
    dash.dependencies.Output('acs-variable', 'options'),
    [
        dash.dependencies.Input('acs-concept', 'value'),
        dash.dependencies.Input('acs-year', 'value')
    ]
)
def set_variables_options(selected_concept, year):
    """given an ACS year and group, this returns a list of the variable options within that group for that year

    Args:
        selected_concept (str): the ACS group chosen by the user
        year (str): the year chosen by the user

    Returns:
        list: returns a list of dict options with 'label' and 'value' as keys. see how `year_options` is formatted above
    """
    variable_url = 'https://api.census.gov/data/%s/acs/acs5/groups/%s.json' % (year, selected_concept)
    variables_data = requests.get(variable_url).json()['variables']
    variables = []
    for key, value in variables_data.items():
        if key[-1] == 'E':
            label = value['label'].replace('Estimate!!', '')
            label = label.replace('!!', ': ')
            variables.append(
                {
                    'label': label,
                    'value': key
                }
            )

    return variables


@app.callback(
    dash.dependencies.Output('acs-table', 'children'),
    [
        dash.dependencies.Input('acs-variable', 'value'),
        dash.dependencies.Input('acs-concept', 'value'),
        dash.dependencies.Input('region-level', 'value'),
        dash.dependencies.Input('acs-year', 'value')
    ]
)
def get_table(acs_variable, acs_concept, region_level, year):
    """Handles the inputs from the user, and returns the data as a datatable

    Args:
        acs_variable (str): ACS variable chosen by the user for what data they want downloaded
        acs_concept (str): ACS group that the variable belongs to (used for renaming columns)
        region_level (str): ACS region definition that the user wants data for
        year (str): Year of ACS data user wants

    Returns:
        list: a list with one item in it - a dt.DataTable. This is dash's way of making a datatable easier on the eyes.
    """
    if type(acs_variable) == str:
        acs_variable = [acs_variable]

    acsColumns = ','.join(acs_variable)
    df = get_acs_table(acsColumns, region_level, acs_concept, year)

    table = dt.DataTable(
        rows=df.to_dict('records'),
        columns = list(df.columns),
        row_selectable=False,
        filterable=True,
        sortable=True,
        editable = False,
        selected_row_indices=[],
        id='acs-full-datatable'
    )

    return [table]


@app.callback(
    dash.dependencies.Output('download-link', 'href'),
    [
        dash.dependencies.Input('acs-full-datatable', 'rows'),
        dash.dependencies.Input('acs-full-datatable', 'columns'),
    ]
)
def update_download_link(data_rows, column_order):
    """Handles the downloading of the data that the user wants

    Args:
        data_rows (list): a list of the rows and columns in the input table
        column_order (list): list of the column names and the order they should be in. if you don't have this, then the output data will be in a different order every time

    Returns:
        str: A url string output for the button to download the data
    """
    df = pd.DataFrame(data_rows)
    df = df[column_order]
    csv_string = df.to_csv(index=False, encoding='utf-8')
    csv_string = "data:text/csv;charset=utf-8," + urllib.parse.quote(csv_string)
    return csv_string


# Dash CSS
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
# Loading screen CSS
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})
app.run_server(debug=False)
