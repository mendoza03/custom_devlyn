def get_line_chart(data):
    return {
        'type': 'line',
        'data': data,
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'display': False,
                }
            },
            'interaction': {
                'intersect': False,
                'mode': 'index',
            },
            'scales': {
                'y': {
                    'grid': {
                        'drawBorder': False,
                        'display': True,
                        'drawOnChartArea': True,
                        'drawTicks': False,
                        'borderDash': [5, 5],
                        'color': 'rgba(255, 255, 255, .2)'
                    },
                    'ticks': {
                        'display': True,
                        'padding': 10,
                        'color': '#f8f9fa',
                        'font': {
                            'size': 14,
                            'weight': 300,
                            'family': 'Roboto',
                            'style': 'normal',
                            'lineHeight': 2
                        },
                    }
                },
                'x': {
                    'grid': {
                        'drawBorder': False,
                        'display': False,
                        'drawOnChartArea': False,
                        'drawTicks': False,
                        'borderDash': [5, 5]
                    },
                    'ticks': {
                        'display': True,
                        'color': '#f8f9fa',
                        'padding': 10,
                        'font': {
                            'size': 14,
                            'weight': 300,
                            'family': 'Roboto',
                            'style': 'normal',
                            'lineHeight': 2
                        },
                    }
                },
            },
        },
    }


def get_bar_chart(data):
    return {
        'type': 'bar',
        'data': data,
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'display': False,
                }
            },
            'interaction': {
                'intersect': False,
                'mode': 'index',
            },
            'scales': {
                'y': {
                    'grid': {
                        'drawBorder': False,
                        'display': True,
                        'drawOnChartArea': True,
                        'drawTicks': False,
                        'borderDash': [5, 5],
                        'color': 'rgba(255, 255, 255, .2)'
                    },
                    'ticks': {
                        'suggestedMin': 0,
                        'suggestedMax': 500,
                        'beginAtZero': True,
                        'padding': 10,
                        'font': {
                            'size': 14,
                            'weight': 300,
                            'family': 'Roboto',
                            'style': 'normal',
                            'lineHeight': 2
                        },
                        'color': '#fff'
                    },
                },
                'x': {
                    'grid': {
                        'drawBorder': False,
                        'display': True,
                        'drawOnChartArea': True,
                        'drawTicks': False,
                        'borderDash': [5, 5],
                        'color': 'rgba(255, 255, 255, .2)'
                    },
                    'ticks': {
                        'display': True,
                        'color': '#f8f9fa',
                        'padding': 10,
                        'font': {
                            'size': 14,
                            'weight': 300,
                            'family': 'Roboto',
                            'style': 'normal',
                            'lineHeight': 2
                        },
                    }
                },
            },
        },
    }


def prepare_chart_data(labels, data):
    datasets = []
    for key, value in data.items():
        datasets.append({
            'label': key,
            'data': value['data'],
            'borderColor': value['color'],
            'pointBackgroundColor': value['color'],

            'fill': True,
            'tension': 0,
            'borderWidth': 4,
            'pointRadius': 5,
            'maxBarThickness': 6,
            'pointBorderColor': 'transparent',
            'backgroundColor': 'transparent',
        })

    return {
        'labels': labels,
        'datasets': datasets,
    }
