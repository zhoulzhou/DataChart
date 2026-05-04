<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  grossRateData: { type: Array, default: () => [] },
  netRateData: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: v => (v * 100).toFixed(2) + '%' },
    legend: { data: ['毛利率', '净利率'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: props.labels },
    yAxis: { type: 'value', axisLabel: { formatter: v => (v * 100).toFixed(0) + '%' } },
    series: [
      { name: '毛利率', type: 'bar', data: props.grossRateData, itemStyle: { color: '#7209b7' } },
      { name: '净利率', type: 'bar', data: props.netRateData, itemStyle: { color: '#4cc9f0' } }
    ]
  }, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch([() => props.labels, () => props.grossRateData, () => props.netRateData], renderChart)
onBeforeUnmount(() => { chart?.dispose() })
</script>

<template>
  <div ref="chartRef" style="width:100%;height:350px;"></div>
</template>
