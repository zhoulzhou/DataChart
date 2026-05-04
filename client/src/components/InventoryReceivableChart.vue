<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  inventoryData: { type: Array, default: () => [] },
  receivableData: { type: Array, default: () => [] }
})

const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['存货', '应收账款'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: props.labels, axisLabel: { formatter: '{value}月' } },
    yAxis: { type: 'value' },
    series: [
      { name: '存货', type: 'line', data: props.inventoryData, smooth: true, itemStyle: { color: '#f8961e' } },
      { name: '应收账款', type: 'line', data: props.receivableData, smooth: true, itemStyle: { color: '#e63946' } }
    ]
  }, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch([() => props.labels, () => props.inventoryData, () => props.receivableData], renderChart)

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" style="width:100%;height:350px;"></div>
</template>
