from dash import Dash, html, dcc, Input
from dash.dependencies import Input, Output

app = Dash(__name__)

app.layout = html.Div([
    html.Button('submit', id = 'numbers'),
    dcc.Input(placeholder = "Enter a valid number",
               id = 'Data', type = 'number'),
    html.H1(id = 'Results')
    ])

@app.callback(Output('Results','children'),
              Input('numbers','n_clicks'))
def play_data(data):
    #if n:
        return f" you enter: {data}"
    #return ""
app.run(debug=True)