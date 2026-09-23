import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
"""
Dash → the main app object.

dcc → Dash Core Components (graphs, dropdowns, sliders, etc.).

html → HTML elements (Div, H1, P, etc.).

Input, Output → used in callbacks for interactivity.
    
    
    
"""
df =  pd.read_csv(r'C:\Users\newle\OneDrive\Desktop\CAI-S2-G1-AI\src\DA\assignments\Dash\Dash.csv')
app = Dash()
app.title = "Sales Interactive Dashboard"
num_cols = df.select_dtypes(include='number').columns
app.layout = html.Div([html.H1("Sales Interactive Dashboard"),
                       html.H5("explore and compare sales data for different governorates"),
                       html.Label("Select a value to show in the pie chart"),
                       dcc.Dropdown(id = 'column-dropdown',
                                    options = [{'label':col, 'value':col} for col in num_cols],
                                    value=num_cols[0]),
                        html.Div([html.H3("Trips by Hour"),
                                  dcc.Graph(id = 'pie-chart' )],
                                      style={
                                        "width": "50%",
                                        "display": "inline-block",
                                        "verticalAlign": "top"
                                        }),
                        html.Div([html.H3("Area bar chart"),                      
                                  dcc.Graph(id = 'bar-chart' )],
                                      style={
                                        "width": "50%",
                                        "display": "inline-block",
                                        "verticalAlign": "top"
                                        }),
                        
                       ])


@app.callback(
    Output('pie-chart', 'figure'),
    Input('column-dropdown', 'value')
)
def update_pie(selected_col):
    # Group by Month and sum the selected column
    grouped = df.groupby('Area')[selected_col].sum().reset_index()

    # Build pie chart
    fig = px.pie(
        grouped,
        names='Area',
        values=selected_col,
        title=f"Distribution of {selected_col} by Area",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    return fig

@app.callback(
    Output('bar-chart', 'figure'),
    Input('column-dropdown', 'value')
)
def update_bar(selected_col):
    # Group by Month and sum the selected column
    grouped = df.groupby('Area')[selected_col].sum().reset_index()

    # Build bar chart
    fig1 = px.bar(
        grouped,
        x='Area',
        y=selected_col,
        title=f"Distribution of {selected_col} by Area",
        color='Area'
    )
    return fig1


# Run server
if __name__ == "__main__":
    app.run(debug=True)