--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) NOT NULL,
  `email` varchar(191) NOT NULL,
  `email_verified_at` timestamp NULL DEFAULT NULL,
  `password` varchar(191) DEFAULT NULL,
  `remember_token` varchar(100) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `shop_id` bigint(20) UNSIGNED DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1696;

--
-- Table structure for table `wallets`
--

CREATE TABLE `wallets` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `total_points` double NOT NULL DEFAULT 0,
  `points_used` double NOT NULL DEFAULT 0,
  `available_points` double NOT NULL DEFAULT 0,
  `customer_id` bigint(20) UNSIGNED DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE `wallets`
  ADD PRIMARY KEY (`id`),
  ADD KEY `wallets_customer_id_foreign` (`customer_id`);
ALTER TABLE `wallets`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1679;
ALTER TABLE `wallets`
  ADD CONSTRAINT `wallets_customer_id_foreign` FOREIGN KEY (`customer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
ALTER TABLE `wallets`
  ADD PRIMARY KEY (`id`),
  ADD KEY `wallets_customer_id_foreign` (`customer_id`);
ALTER TABLE `wallets`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1679;




CREATE TABLE `wishlists` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `product_id` bigint(20) UNSIGNED NOT NULL,
  `variation_option_id` bigint(20) UNSIGNED DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE `wishlists`
  ADD PRIMARY KEY (`id`),
  ADD KEY `wishlists_user_id_foreign` (`user_id`),
  ADD KEY `wishlists_product_id_foreign` (`product_id`),
  ADD KEY `wishlists_variation_option_id_foreign` (`variation_option_id`);
ALTER TABLE `wishlists`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;
ALTER TABLE `wishlists`
  ADD CONSTRAINT `wishlists_product_id_foreign` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `wishlists_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `wishlists_variation_option_id_foreign` FOREIGN KEY (`variation_option_id`) REFERENCES `variation_options` (`id`) ON DELETE CASCADE;




--
-- Table structure for table `user_profiles`
--
CREATE TABLE `user_profiles` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `avatar` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`avatar`)),
  `bio` text DEFAULT NULL,
  `socials` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`socials`)),
  `contact` varchar(191) DEFAULT NULL,
  `notifications` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`notifications`)),
  `customer_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `user_profiles`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;
ALTER TABLE `user_profiles`
  ADD CONSTRAINT `user_profiles_customer_id_foreign` FOREIGN KEY (`customer_id`) REFERENCES `users` (`id`);
ALTER TABLE `user_profiles`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_profiles_customer_id_foreign` (`customer_id`);


--
-- Table structure for table `shops`
--

CREATE TABLE `shops` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `owner_id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) DEFAULT NULL,
  `slug` varchar(191) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `cover_image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`cover_image`)),
  `logo` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`logo`)),
  `is_active` tinyint(1) NOT NULL DEFAULT 0,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`address`)),
  `settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`settings`)),
  `notifications` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`notifications`)),
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE `shops`
  ADD PRIMARY KEY (`id`),
  ADD KEY `shops_owner_id_foreign` (`owner_id`);
ALTER TABLE `shops`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;
ALTER TABLE `shops`
  ADD CONSTRAINT `shops_owner_id_foreign` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`);


--
-- Table structure for table `address`
--

CREATE TABLE `address` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(191) NOT NULL,
  `type` varchar(191) NOT NULL,
  `default` tinyint(1) NOT NULL DEFAULT 0,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`address`)),
  `location` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`location`)),
  `customer_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `address`
  ADD PRIMARY KEY (`id`),
  ADD KEY `address_customer_id_foreign` (`customer_id`);
ALTER TABLE `address`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;
ALTER TABLE `address`
  ADD CONSTRAINT `address_customer_id_foreign` FOREIGN KEY (`customer_id`) REFERENCES `users` (`id`);


--
-- Table structure for table `user_shop`
--

CREATE TABLE `user_shop` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `shop_id` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `user_shop`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_shop_shop_id_foreign` (`shop_id`),
  ADD KEY `user_shop_user_id_foreign` (`user_id`);

ALTER TABLE `user_shop`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;
ALTER TABLE `user_shop`
  ADD CONSTRAINT `user_shop_shop_id_foreign` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `user_shop_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;


CREATE TABLE `products` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) NOT NULL,
  `slug` varchar(191) NOT NULL,
  `description` text DEFAULT NULL,
  `type_id` bigint(20) UNSIGNED NOT NULL,
  `price` double DEFAULT NULL,
  `shop_id` bigint(20) UNSIGNED DEFAULT NULL,
  `sale_price` double DEFAULT NULL,
  `purchase_price` double DEFAULT NULL,
  `language` varchar(191) NOT NULL DEFAULT 'en',
  `min_price` double(8,2) DEFAULT NULL,
  `max_price` double(8,2) DEFAULT NULL,
  `sku` varchar(191) DEFAULT NULL,
  `bar_code` varchar(250) DEFAULT NULL,
  `quantity` int(11) NOT NULL DEFAULT 0,
  `in_stock` tinyint(1) NOT NULL DEFAULT 1,
  `is_taxable` tinyint(1) NOT NULL DEFAULT 0,
  `shipping_class_id` bigint(20) UNSIGNED DEFAULT NULL,
  `status` enum('publish','draft') NOT NULL DEFAULT 'publish',
  `product_type` enum('simple','variable') NOT NULL DEFAULT 'simple',
  `unit` varchar(191) NOT NULL,
  `height` varchar(191) DEFAULT NULL,
  `width` varchar(191) DEFAULT NULL,
  `length` varchar(191) DEFAULT NULL,
  `image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`image`)),
  `video` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`video`)),
  `gallery` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`gallery`)),
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `author_id` bigint(20) UNSIGNED DEFAULT NULL,
  `manufacturer_id` bigint(20) UNSIGNED DEFAULT NULL,
  `is_digital` tinyint(1) NOT NULL DEFAULT 0,
  `is_external` tinyint(1) NOT NULL DEFAULT 0,
  `external_product_url` varchar(191) DEFAULT NULL,
  `external_product_button_text` varchar(191) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `products`
  ADD PRIMARY KEY (`id`),
  ADD KEY `products_type_id_foreign` (`type_id`),
  ADD KEY `products_shipping_class_id_foreign` (`shipping_class_id`),
  ADD KEY `products_shop_id_foreign` (`shop_id`),
  ADD KEY `products_author_id_foreign` (`author_id`),
  ADD KEY `products_manufacturer_id_foreign` (`manufacturer_id`);

ALTER TABLE `products`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1174;
ALTER TABLE `products`
  ADD CONSTRAINT `products_author_id_foreign` FOREIGN KEY (`author_id`) REFERENCES `authors` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `products_manufacturer_id_foreign` FOREIGN KEY (`manufacturer_id`) REFERENCES `manufacturers` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `products_shipping_class_id_foreign` FOREIGN KEY (`shipping_class_id`) REFERENCES `shipping_classes` (`id`),
  ADD CONSTRAINT `products_shop_id_foreign` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `products_type_id_foreign` FOREIGN KEY (`type_id`) REFERENCES `types` (`id`) ON DELETE CASCADE;

--
-- Table structure for table `categories`
--

CREATE TABLE `categories` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) NOT NULL,
  `slug` varchar(191) NOT NULL,
  `language` varchar(191) NOT NULL DEFAULT 'en',
  `icon` varchar(191) DEFAULT NULL,
  `image` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`image`)),
  `details` text DEFAULT NULL,
  `parent` bigint(20) UNSIGNED DEFAULT NULL,
  `type_id` bigint(20) UNSIGNED NOT NULL,
  `admin_commission_rate` double DEFAULT NULL,
  `is_active` tinyint(4) NOT NULL DEFAULT 1,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `categories`
  ADD PRIMARY KEY (`id`),
  ADD KEY `categories_parent_foreign` (`parent`),
  ADD KEY `categories_type_id_foreign` (`type_id`);
ALTER TABLE `categories`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=235;
ALTER TABLE `categories`
  ADD CONSTRAINT `categories_parent_foreign` FOREIGN KEY (`parent`) REFERENCES `categories` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `categories_type_id_foreign` FOREIGN KEY (`type_id`) REFERENCES `types` (`id`) ON DELETE CASCADE;


--
-- Table structure for table `roles`
--

CREATE TABLE `roles` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) NOT NULL,
  `guard_name` varchar(191) NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


ALTER TABLE `roles`
  ADD PRIMARY KEY (`id`);
ALTER TABLE `roles`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;
--
-- Table structure for table `role_has_permissions`
--

CREATE TABLE `role_has_permissions` (
  `permission_id` bigint(20) UNSIGNED NOT NULL,
  `role_id` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
--
-- Indexes for table `role_has_permissions`
--
ALTER TABLE `role_has_permissions`
  ADD PRIMARY KEY (`permission_id`,`role_id`),
  ADD KEY `role_has_permissions_role_id_foreign` (`role_id`);
ALTER TABLE `role_has_permissions`
  ADD CONSTRAINT `role_has_permissions_permission_id_foreign` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `role_has_permissions_role_id_foreign` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE;
--
-- Table structure for table `model_has_roles`
--

CREATE TABLE `model_has_roles` (
  `role_id` bigint(20) UNSIGNED NOT NULL,
  `model_type` varchar(191) NOT NULL,
  `model_id` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
--
ALTER TABLE `model_has_roles`
  ADD PRIMARY KEY (`role_id`,`model_id`,`model_type`),
  ADD KEY `model_has_roles_model_id_model_type_index` (`model_id`,`model_type`);
ALTER TABLE `model_has_roles`
  ADD CONSTRAINT `model_has_roles_role_id_foreign` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE;

--
-- Table structure for table `permissions`
--

CREATE TABLE `permissions` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(191) NOT NULL,
  `guard_name` varchar(191) NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE `permissions`
  ADD PRIMARY KEY (`id`);
ALTER TABLE `permissions`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

  --
-- Table structure for table `model_has_permissions`
--

CREATE TABLE `model_has_permissions` (
  `permission_id` bigint(20) UNSIGNED NOT NULL,
  `model_type` varchar(191) NOT NULL,
  `model_id` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE `model_has_permissions`
  ADD PRIMARY KEY (`permission_id`,`model_id`,`model_type`),
ALTER TABLE `model_has_permissions`
  ADD CONSTRAINT `model_has_permissions_permission_id_foreign` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE;
