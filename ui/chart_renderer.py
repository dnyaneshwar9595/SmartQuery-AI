import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_chart(chart_config: dict, unique_id: str = None):
    """
    Render a Plotly chart from a chart_config dictionary.
    
    Expected chart_config keys:
        chart_type: str  — pie, bar, bar_horizontal, line, scatter, area, table
        title:      str  — chart title
        columns:    list  — column names (need at least 2 for most charts)
        data:       list  — list of rows (each row is a list of values)
    """
    if not chart_config:
        return

    chart_type = chart_config.get('chart_type', 'table')
    title      = chart_config.get('title', 'Visualization')
    columns    = chart_config.get('columns', [])
    data       = chart_config.get('data', [])
    
    # Convert to DataFrame
    df = pd.DataFrame(data, columns=columns)
    
    if df.empty:
        st.warning("No data to display")
        return
    
    # Safety: most charts need at least 2 columns — fall back to table
    if len(columns) < 2 and chart_type != 'table':
        st.info(f"Only {len(columns)} column(s) available — showing as table instead of {chart_type}.")
        chart_type = 'table'
    
    # Generate unique key
    if unique_id is None:
        import hashlib
        unique_id = hashlib.md5(str(data).encode()).hexdigest()[:10]
    
    st.subheader(f"📊 {title}")
    
    # ==================== PIE CHART ====================
    if chart_type == 'pie':
        fig = px.pie(
            df,
            names=columns[0],
            values=columns[1],
            title=title,
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=12
        )
        st.plotly_chart(fig, width='stretch', key=f"pie_{unique_id}")
    
    # ==================== BAR CHART ====================
    elif chart_type == 'bar':
        fig = px.bar(
            df,
            x=columns[0],
            y=columns[1],
            title=title,
            color=columns[0],
            text=columns[1]
        )
        fig.update_traces(
            texttemplate='%{text:.2f}',
            textposition='outside'
        )
        fig.update_layout(
            showlegend=False,
            xaxis_title=columns[0].title(),
            yaxis_title=columns[1].title()
        )
        st.plotly_chart(fig, width='stretch', key=f"bar_{unique_id}")
    
    # ==================== HORIZONTAL BAR ====================
    elif chart_type == 'bar_horizontal':
        fig = px.bar(
            df,
            x=columns[1],
            y=columns[0],
            orientation='h',
            title=title,
            color=columns[0],
            text=columns[1]
        )
        fig.update_traces(
            texttemplate='%{text:.2f}',
            textposition='outside'
        )
        fig.update_layout(
            showlegend=False,
            height=max(400, len(df) * 30)
        )
        st.plotly_chart(fig, width='stretch', key=f"barh_{unique_id}")
    
    # ==================== LINE CHART ====================
    elif chart_type == 'line':
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if len(numeric_cols) > 1:
            fig = go.Figure()
            for col in numeric_cols:
                fig.add_trace(go.Scatter(
                    x=df[columns[0]],
                    y=df[col],
                    mode='lines+markers',
                    name=col,
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
            fig.update_layout(
                title=title,
                xaxis_title=columns[0].title(),
                yaxis_title="Value",
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
        else:
            fig = px.line(
                df,
                x=columns[0],
                y=columns[1],
                title=title,
                markers=True
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8))

        st.plotly_chart(fig, width='stretch', key=f"line_{unique_id}")

    # ==================== SCATTER PLOT ====================
    elif chart_type == 'scatter':
        color_col = columns[2] if len(columns) >= 3 else None
        
        fig = px.scatter(
            df,
            x=columns[0],
            y=columns[1],
            color=color_col,
            title=title,
            size_max=15,
            trendline="ols" if len(df) > 5 else None
        )
        fig.update_traces(marker=dict(size=12, line=dict(width=2)))
        st.plotly_chart(fig, width='stretch', key=f"scatter_{unique_id}")
    
    # ==================== AREA CHART ====================
    elif chart_type == 'area':
        fig = px.area(
            df,
            x=columns[0],
            y=columns[1],
            title=title
        )
        st.plotly_chart(fig, width='stretch', key=f"area_{unique_id}")
    
    # ==================== TABLE ====================
    else:
        st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            key=f"table_{unique_id}"
        )