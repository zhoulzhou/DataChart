<script setup>
import { ref, onMounted, watch, onBeforeUnmount, computed } from 'vue'
import { init, use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  title: { type: String, default: '' },
  labels: { type: Array, default: () => [] },
  data: { type: Array, default: () => [] },
  color: { type: String, default: '#4361ee' },
  yMax: { type: Number, default: undefined },
  growthData: { type: Array, default: () => [] },
  growthColor: { type: String, default: '#e63946' },
  growthLabel: { type: String, default: '同比增速' }
})

const chartRef = ref(null)
let chart = null

const hasGrowth = computed(() => props.growthData && props.growthData.some(v => v != null))

function renderChart() {
  if (!chart) {
    console.log('[MetricBarChart] renderChart: chart 未初始化, 跳过')
    return
  }
  console.log(`[MetricBarChart] renderChart: "${props.title}" labels=${props.labels?.length} data=${props.data?.length} hasGrowth=${hasGrowth.value}`)
  if (props.data && props.data.length > 0) {
    console.log(`[MetricBarChart] data 前3项:`, props.data.slice(0, 3))
  }

  const series = [
    { name: props.title, type: 'bar', data: props.data, itemStyle: { color: props.color } }
  ]
  const yAxis = [
    { type: 'value', max: props.yMax, minInterval: 1, axisLabel: { formatter: v => Math.round(v) } }
  ]
  const grid = { left: '3%', right: '4%', bottom: '3%', containLabel: true }

  if (hasGrowth.value && props.growthData.length > 0) {
    grid.right = '8%'
    yAxis.push({
      type: 'value',
      axisLabel: { formatter: v => Math.round(v) + '%' },
      splitLine: { show: false }
    })
    series.push({
      name: props.growthLabel,
      type: 'line',
      yAxisIndex: 1,
      data: props.growthData,
      itemStyle: { color: props.growthColor },
      lineStyle: { color: props.growthColor, width: 2 },
      symbol: 'circle',
      symbolSize: 6,
      connectNulls: false
    })
  }

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = '<strong>' + (params[0]?.axisValue || '') + '</strong><br/>'
        params.forEach(p => {
          if (p.seriesName === props.growthLabel) {
            html += p.marker + p.seriesName + ': ' + (p.value != null ? Math.round(p.value) + '%' : '-') + '<br/>'
          } else {
            html += p.marker + p.seriesName + ': ' + Math.round(p.value).toLocaleString() + '<br/>'
          }
        })
        return html
      }
    },
    grid,
    xAxis: { type: 'category', data: props.labels, axisLabel: { rotate: props.labels.length > 12 ? 45 : 0 } },
    yAxis,
    series
  }, true)
}

onMounted(() => {
  console.log(`[MetricBarChart] onMounted: "${props.title}" chartRef=${!!chartRef.value}`)
  if (!chartRef.value) {
    console.log('[MetricBarChart] FATAL: chartRef 为 null, 无法初始化图表!')
    return
  }
  chart = init(chartRef.value)
  console.log(`[MetricBarChart] chart 初始化完成: "${props.title}"`)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch([() => props.labels, () => props.data, () => props.yMax, () => props.growthData, () => props.growthLabel], (newVals) => {
  console.log(`[MetricBarChart] watch 触发: "${props.title}" labels=${newVals[0]?.length} data=${newVals[1]?.length}`)
  renderChart()
})
onBeforeUnmount(() => { chart?.dispose() })
</script>

<template>
  <div ref="chartRef" style="width:100%;height:320px;"></div>
</template>
