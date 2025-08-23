import Link from "next/link"
import { ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import DotGridShader from "@/components/DotGridShader"
import SmoothScrollLink from "@/components/smooth-scroll-link"

import ProjectCard from "@/components/project-card"
import AnimatedHeading from "@/components/animated-heading"
import RevealOnView from "@/components/reveal-on-view"

export default function Page() {
  const projects = [
    {
      title: "单个URL解析",
      subtitle: "输入URL快速转换为结构化数据",
      imageSrc: "/images/project-1.webp",
      tags: ["URL", "解析", "单个"],
      href: "#single-url",
      priority: true,
      gradientFrom: "#0f172a",
      gradientTo: "#6d28d9",
    },
    {
      title: "批量处理",
      subtitle: "批量URL处理和数据转换",
      imageSrc: "/images/project-2.webp",
      tags: ["批量", "自动化", "效率"],
      href: "#batch-process",
      priority: false,
      gradientFrom: "#111827",
      gradientTo: "#2563eb",
    },
    {
      title: "处理结果",
      subtitle: "查看和管理转换结果",
      imageSrc: "/images/project-3.webp",
      tags: ["结果", "管理", "导出"],
      href: "#results",
      priority: false,
      gradientFrom: "#0b132b",
      gradientTo: "#5bc0be",
    },
    {
      title: "设置",
      subtitle: "系统状态和配置管理",
      imageSrc: "/images/project-4.webp",
      tags: ["系统", "配置", "状态"],
      href: "#setting",
      priority: false,
      gradientFrom: "#0f172a",
      gradientTo: "#10b981",
    },
  ]

  return (
    <main className="bg-neutral-950 text-white">
      {/* HERO: full-viewport row. Left is sticky; right scrolls internally. */}
      <section className="px-4 pt-4 pb-16 lg:pb-4">
        <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[420px_1fr]">
          {/* LEFT: sticky and full height, no cut off */}
          <aside className="lg:sticky lg:top-4 lg:h-[calc(100svh-2rem)]">
            <RevealOnView
              as="div"
              intensity="hero"
              className="relative flex h-full flex-col justify-between overflow-hidden rounded-3xl border border-white/10 bg-neutral-900/60 p-6 sm:p-8"
              staggerChildren
            >
              {/* Texture background */}
              <div className="pointer-events-none absolute inset-0 opacity-5 mix-blend-soft-light">
                <DotGridShader />
              </div>
              <div>
                {/* Wordmark */}
                <div className="mb-8 flex items-center gap-2">
                  <div className="text-2xl font-extrabold tracking-tight">Zhil</div>
                  <div className="h-2 w-2 rounded-full bg-white/60" aria-hidden="true" />
                </div>

                {/* Headline with intro blur effect */}
                <AnimatedHeading
                  className="text-4xl font-black leading-[1.05] tracking-tight sm:text-5xl"
                  lines={["Information", "Finely crafted"]}
                />

                <p className="mt-4 max-w-[42ch] text-lg text-white/70">
                  Zhil 由 LLM 驱动，深入理解任意网页，将纷繁的信息提炼为精准、规整的 Notion 条目。你只管收藏，剩下的，交给它就好
                </p>

                {/* CTAs */}
                <div className="mt-6 flex flex-wrap items-center gap-3">
                  <Button asChild size="lg" className="rounded-full font-bold">
                    <SmoothScrollLink href="#single-url" offset={16}>
                      快速开始
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </SmoothScrollLink>
                  </Button>
                  <Button asChild size="lg" variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white font-bold">
                    <SmoothScrollLink href="#batch-process" offset={16}>
                      批量处理
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </SmoothScrollLink>
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <Button asChild size="lg" variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white font-bold">
                    <SmoothScrollLink href="#results" offset={16}>
                      处理结果
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </SmoothScrollLink>
                  </Button>
                  <Button asChild size="lg" variant="outline" className="rounded-full border-white/20 bg-transparent text-white hover:bg-white/10 hover:text-white font-bold">
                    <SmoothScrollLink href="#setting" offset={16}>
                      设置中心
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </SmoothScrollLink>
                  </Button>
                </div>

                {/* Trusted by */}
                <div className="mt-10">
                  <p className="mb-3 text-xs font-semibold tracking-widest text-white/50">核心功能特性</p>
                  <ul className="grid grid-cols-2 gap-x-7 gap-y-3 text-lg font-black text-white/25 sm:grid-cols-3">
                    <li>URL解析</li>
                    <li>批量处理</li>
                    <li>智能提取</li>
                    <li>结构化转换</li>
                    <li>Notion集成</li>
                    <li>数据管理</li>
                  </ul>
                </div>
              </div>
            </RevealOnView>
          </aside>

          {/* RIGHT: simplified, no internal card or horizontal carousel */}
          <div className="space-y-4">
            {projects.map((p, idx) => (
              <div 
                key={p.title} 
                id={p.href.replace('#', '')} 
                className="scroll-mt-4"
                style={{ scrollMarginTop: '16px' }}
              >
                <ProjectCard
                  title={p.title}
                  subtitle={p.subtitle}
                  imageSrc={p.imageSrc}
                  tags={p.tags}
                  href={p.href}
                  priority={p.priority}
                  gradientFrom={p.gradientFrom}
                  gradientTo={p.gradientTo}
                  imageContainerClassName="lg:h-full"
                  containerClassName="lg:h-[calc(100svh-2rem)]"
                  revealDelay={idx * 0.06}
                />
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  )
}
