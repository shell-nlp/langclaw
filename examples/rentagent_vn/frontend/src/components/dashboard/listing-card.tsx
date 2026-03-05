"use client";

import { MapPin, Bed, Maximize2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useListingStore } from "@/stores/listing-store";
import type { Listing } from "@/types";

interface ListingCardProps {
  listing: Listing;
  campaignId: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  facebook: "FB",
  "nhatot.com": "NT",
  "batdongsan.com.vn": "BDS",
};

export function ListingCard({ listing }: ListingCardProps) {
  const { selectListing } = useListingStore();

  const platformLabel =
    PLATFORM_LABELS[listing.source_platform || ""] ||
    listing.source_platform?.slice(0, 3)?.toUpperCase() ||
    "";

  return (
    <Card
      className="p-3 cursor-pointer hover:shadow-md transition-shadow border-border/50"
      onClick={() => selectListing(listing)}
    >
      <div className="flex gap-3">
        {/* Thumbnail */}
        {listing.thumbnail_url ? (
          <img
            src={listing.thumbnail_url}
            alt=""
            className="w-16 h-16 rounded-md object-cover bg-muted shrink-0"
            loading="lazy"
          />
        ) : (
          <div className="w-16 h-16 rounded-md bg-muted flex items-center justify-center shrink-0">
            <Maximize2 className="h-4 w-4 text-muted-foreground" />
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {listing.title || "Không có tiêu đề"}
          </p>

          {/* Price */}
          <p className="text-sm font-semibold text-primary mt-0.5">
            {listing.price_display || formatPrice(listing.price_vnd)}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            {listing.district && (
              <span className="flex items-center gap-0.5">
                <MapPin className="h-3 w-3" />
                {listing.district}
              </span>
            )}
            {listing.bedrooms != null && (
              <span className="flex items-center gap-0.5">
                <Bed className="h-3 w-3" />
                {listing.bedrooms}PN
              </span>
            )}
            {listing.area_sqm != null && (
              <span>{listing.area_sqm}m²</span>
            )}
          </div>
        </div>
      </div>

      {/* Bottom badges */}
      <div className="flex items-center gap-1.5 mt-2">
        {platformLabel && (
          <Badge variant="outline" className="text-[10px] h-4 px-1">
            {platformLabel}
          </Badge>
        )}
        {listing.landlord_phone && (
          <Badge variant="outline" className="text-[10px] h-4 px-1 text-green-600">
            Zalo
          </Badge>
        )}
      </div>
    </Card>
  );
}

function formatPrice(priceVnd: number | null): string {
  if (!priceVnd) return "Liên hệ";
  if (priceVnd >= 1_000_000) {
    return `${(priceVnd / 1_000_000).toFixed(1).replace(".0", "")} triệu/th`;
  }
  return `${priceVnd.toLocaleString("vi-VN")} đ/th`;
}
