#!/usr/bin/env python

import dfply as ply
from dfply import X as x
import pandas as pd
import marketbeat
from dash import Dash, Input, Output, html, dcc, no_update
from plotly_calplot import calplot
from plotly import graph_objects as go
from millify import millify, prettify
import cachetools

app = Dash(external_stylesheets=[
    'https://unpkg.com/@picocss/pico@latest/css/pico.min.css',
    '/assets/style.css',
])

app.index_string = '''
<!DOCTYPE html>
<html data-theme="light">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        <main class="container">
            {%app_entry%}
        </main>
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    html.H1('Post-Lockup Liquidity Heatmap'),
    html.Div([
        html.Div([
            html.Fieldset([
                dcc.RadioItems(
                    id='offer-size',
                    value='curr',
                    options={
                        'ipo': 'IPO Offer Size',
                        'curr': 'Current Offer Size'
                    },
                    inline=True,
                    className='grid'
                ),
            ]),
            dcc.Graph(
                id='heatmap',
                responsive=True,
                clear_on_unhover=True,
            ),
            dcc.Tooltip(
                id='tooltip',
                className='tooltip',
                direction='bottom',
            ),
        ]),
        html.Article(
            dcc.Markdown(
                '''
                Hi AC!

                Michael tells me you were wondering what kinds of tools you
                could build with the data you have, so I decided to take a
                couple of hours and see for myself.

                What you're looking at here is a live heatmap of the amount of
                liquidity about to hit the market post-lockup(s).  Hovering over
                the dates of interests will show you the exact per-share
                breakdown.

                I'm automatically scraping this off of publicly available
                websites, but this would be much easier (and more accurate) with
                direct access to the Bloomberg API &mdash; which ML has &mdash;
                combined with Michael's prospectus analysis (translated to
                programmatic conditions).

                If we further enrich this information with distribution data I'm
                sure even more interestign trends would emerge to a trained eye
                like yours; To a data/tech-head like me though, I can't help but
                wonder what a basic GLM with some interaction
                variables/nonlinearities thrown in could extract/predict from
                all of that information.

                Happy to chat about this any time!

                Cheers,

                Uros
                '''
            ),
            className='note',
        )
    ],
        className='grid',
    )
])

@app.callback(
    Output('tooltip', 'show'),
    Output('tooltip', 'bbox'),
    Output('tooltip', 'children'),
    Input('heatmap', 'hoverData'),
)
def update_tooltip(hover_data):
    df = get_data()

    try:
        pt = hover_data['points'][0]
        bbox = pt['bbox']
        date = pd.to_datetime(pt['customdata'][0])

        matching_entries = (df >>
            ply.mask(x.expiration_date == date)
        )

        children = []
        for _, row in matching_entries.iterrows():
            children.append(
                html.Div([
                    html.Div([
                        html.H2(row.ticker),
                        html.Img(src=row.logo_url),
                    ],
                    className='grid stock'),
                    html.P(row['name']),
                    html.P(f'No. Shares: {millify(row.num_shares)}'),
                    html.P(f'IPO Price: {prettify(row.initial_price)}'),
                    html.P(f'IPO Offer Size: {millify(row.offer_size)}'),
                    html.P(f'Current Price: {prettify(row.price)}'),
                    html.P(f'Current Offer Size: {millify(row.current_offer_size)}'),
                    html.P(f'Date: {row.expiration_date.strftime("%d %B %Y")}'),
                ])
            )

        return True, bbox, children
    except:
        return False, None, None

@cachetools.cached(cachetools.TTLCache(maxsize=1, ttl=24 * 60 * 60))
def get_data() -> pd.DataFrame:
    df = marketbeat.get_lockup_data()

    df_augmented = (
        df >>
        ply.mutate(current_offer_size=x.price * x.num_shares) >>
        ply.group_by(x.expiration_date.dt.date) >>
        ply.mutate(
            daily_offer_size=x.offer_size.sum(),
            daily_current_offer_size=x.current_offer_size.sum()
        )
    )
    
    return df_augmented


@app.callback(
    Output('heatmap', 'figure'),
    Input('offer-size', 'value')
)
def update_heatmap(selected_figure):
    try:
        match selected_figure:
            case 'ipo': y_metric = 'daily_offer_size'
            case 'curr': y_metric = 'daily_current_offer_size'

        df = get_data()

        fig = calplot(
            data=df,
            x='expiration_date',
            y=y_metric,
        )

        layout = go.Layout(
            yaxis=dict(scaleanchor="x", scaleratio=1),
            xaxis=dict(
                range=[
                    min(df['expiration_date'].dt.week) - 1,
                    max(df['expiration_date'].dt.week) + 2,
                ]
            )
        )

        fig.update_layout(layout)
        fig.update_traces(hoverinfo="none", hovertemplate=None)

        return fig
    except:
        return no_update


if __name__ == '__main__':
    app.run_server(debug=True)
