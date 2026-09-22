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
                       dcc.Graph(id = 'pie-chart' )

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


# Run server
if __name__ == "__main__":
    app.run(debug=True)