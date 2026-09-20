import { createFileRoute } from "@tanstack/react-router";
import App from "@/App";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SkyResolve — Airline Support Operations" },
      {
        name: "description",
        content: "Policy-first flight disruption resolution for airline support teams.",
      },
      { property: "og:title", content: "SkyResolve — Airline Support Operations" },
      {
        property: "og:description",
        content: "Policy-first flight disruption resolution for airline support teams.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: App,
});
