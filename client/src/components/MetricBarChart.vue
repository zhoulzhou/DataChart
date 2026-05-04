<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  title: { type: String, default: '' },
  labels: { type: Array, default: () => [] },
  data: { type: Array, default: () => [] },
  color: { type: String, default: '#4361ee' },
  yMax: { type: Number, default: undefined }
})

const chartRef = ref(null)
let chart = null

function renderChart() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: props.labels, axisLabel: { rotate: props.labels.length > 12 ? 45 : 0 } },
    yAxis: { type: 'value', max: props.yMax },
    series: [{ name: props.title, type: 'bar', data: props.data, itemStyle: { color: props.color } }]
  }, true)
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  renderChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch([() => props.labels, () => props.data, () => props.yMax], renderChart)
onBeforeUnmount(() => { chart?.dispose() })
</script>

<template>
  <div ref="chartRef" style="width:100%;height:320px;"></div>
</template>
