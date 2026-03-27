/*
 Navicat Premium Data Transfer

 Source Server         : MySQL
 Source Server Type    : MySQL
 Source Server Version : 80032
 Source Host           : localhost:3306
 Source Schema         : nus_event

 Target Server Type    : MySQL
 Target Server Version : 80032
 File Encoding         : 65001

 Date: 10/03/2026 21:50:29
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for travel_times
-- ----------------------------
DROP TABLE IF EXISTS `travel_times`;
CREATE TABLE `travel_times`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `loc_from` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `loc_to` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `mode` enum('walk','bus','car','bike','mrt') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'walk',
  `minutes` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uniq_loc_mode`(`loc_from`, `loc_to`, `mode`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 83 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of travel_times
-- ----------------------------
INSERT INTO `travel_times` VALUES (1, 'AS5', 'BIZ2', 'bus', 2);
INSERT INTO `travel_times` VALUES (2, 'AS5', 'PGP', 'bus', 5);
INSERT INTO `travel_times` VALUES (3, 'AS5', 'KRMRT', 'bus', 9);
INSERT INTO `travel_times` VALUES (4, 'AS5', 'LT27', 'bus', 11);
INSERT INTO `travel_times` VALUES (5, 'AS5', 'OPPUHC', 'bus', 14);
INSERT INTO `travel_times` VALUES (6, 'AS5', 'CLB', 'bus', 2);
INSERT INTO `travel_times` VALUES (7, 'BIZ2', 'PGP', 'bus', 3);
INSERT INTO `travel_times` VALUES (8, 'BIZ2', 'KRMRT', 'bus', 7);
INSERT INTO `travel_times` VALUES (9, 'BIZ2', 'LT27', 'bus', 9);
INSERT INTO `travel_times` VALUES (10, 'BIZ2', 'OPPUHC', 'bus', 12);
INSERT INTO `travel_times` VALUES (11, 'BIZ2', 'CLB', 'bus', 4);
INSERT INTO `travel_times` VALUES (12, 'PGP', 'KRMRT', 'bus', 4);
INSERT INTO `travel_times` VALUES (13, 'PGP', 'LT27', 'bus', 6);
INSERT INTO `travel_times` VALUES (14, 'PGP', 'OPPUHC', 'bus', 9);
INSERT INTO `travel_times` VALUES (15, 'PGP', 'CLB', 'bus', 12);
INSERT INTO `travel_times` VALUES (16, 'KRMRT', 'LT27', 'bus', 2);
INSERT INTO `travel_times` VALUES (17, 'KRMRT', 'OPPUHC', 'bus', 5);
INSERT INTO `travel_times` VALUES (18, 'KRMRT', 'CLB', 'bus', 8);
INSERT INTO `travel_times` VALUES (19, 'LT27', 'OPPUHC', 'bus', 3);
INSERT INTO `travel_times` VALUES (20, 'LT27', 'CLB', 'bus', 6);
INSERT INTO `travel_times` VALUES (21, 'OPPUHC', 'CLB', 'bus', 3);
INSERT INTO `travel_times` VALUES (22, 'CLB', 'UHC', 'bus', 4);
INSERT INTO `travel_times` VALUES (23, 'CLB', 'LT27', 'bus', 6);
INSERT INTO `travel_times` VALUES (24, 'CLB', 'KRMRT', 'bus', 8);
INSERT INTO `travel_times` VALUES (25, 'CLB', 'PGP', 'bus', 13);
INSERT INTO `travel_times` VALUES (26, 'CLB', 'BIZ2', 'bus', 4);
INSERT INTO `travel_times` VALUES (27, 'CLB', 'AS5', 'bus', 2);
INSERT INTO `travel_times` VALUES (28, 'UHC', 'LT27', 'bus', 2);
INSERT INTO `travel_times` VALUES (29, 'UHC', 'KRMRT', 'bus', 4);
INSERT INTO `travel_times` VALUES (30, 'UHC', 'PGP', 'bus', 8);
INSERT INTO `travel_times` VALUES (31, 'UHC', 'BIZ2', 'bus', 13);
INSERT INTO `travel_times` VALUES (32, 'UHC', 'AS5', 'bus', 14);
INSERT INTO `travel_times` VALUES (33, 'LT27', 'KRMRT', 'bus', 2);
INSERT INTO `travel_times` VALUES (34, 'LT27', 'PGP', 'bus', 6);
INSERT INTO `travel_times` VALUES (35, 'LT27', 'BIZ2', 'bus', 11);
INSERT INTO `travel_times` VALUES (36, 'LT27', 'AS5', 'bus', 12);
INSERT INTO `travel_times` VALUES (37, 'KRMRT', 'PGP', 'bus', 4);
INSERT INTO `travel_times` VALUES (38, 'KRMRT', 'BIZ2', 'bus', 9);
INSERT INTO `travel_times` VALUES (39, 'KRMRT', 'AS5', 'bus', 10);
INSERT INTO `travel_times` VALUES (40, 'PGP', 'BIZ2', 'bus', 4);
INSERT INTO `travel_times` VALUES (41, 'PGP', 'AS5', 'bus', 5);
INSERT INTO `travel_times` VALUES (42, 'BIZ2', 'AS5', 'bus', 2);
INSERT INTO `travel_times` VALUES (43, 'BIZ2', 'MUSEUM', 'bus', 7);
INSERT INTO `travel_times` VALUES (44, 'BIZ2', 'UTOWN', 'bus', 9);
INSERT INTO `travel_times` VALUES (45, 'AS5', 'MUSEUM', 'bus', 5);
INSERT INTO `travel_times` VALUES (46, 'AS5', 'UTOWN', 'bus', 7);
INSERT INTO `travel_times` VALUES (47, 'CLB', 'MUSEUM', 'bus', 3);
INSERT INTO `travel_times` VALUES (48, 'CLB', 'UTOWN', 'bus', 5);
INSERT INTO `travel_times` VALUES (49, 'MUSEUM', 'BIZ2', 'bus', 7);
INSERT INTO `travel_times` VALUES (50, 'MUSEUM', 'AS5', 'bus', 5);
INSERT INTO `travel_times` VALUES (51, 'MUSEUM', 'CLB', 'bus', 3);
INSERT INTO `travel_times` VALUES (52, 'MUSEUM', 'UTOWN', 'bus', 2);
INSERT INTO `travel_times` VALUES (53, 'UTOWN', 'BIZ2', 'bus', 9);
INSERT INTO `travel_times` VALUES (54, 'UTOWN', 'AS5', 'bus', 7);
INSERT INTO `travel_times` VALUES (55, 'UTOWN', 'CLB', 'bus', 5);
INSERT INTO `travel_times` VALUES (56, 'UTOWN', 'MUSEUM', 'bus', 2);
INSERT INTO `travel_times` VALUES (63, 'UTOWN', 'UHC', 'bus', 4);
INSERT INTO `travel_times` VALUES (64, 'UTOWN', 'LT27', 'bus', 6);
INSERT INTO `travel_times` VALUES (65, 'UTOWN', 'KRMRT', 'bus', 8);
INSERT INTO `travel_times` VALUES (66, 'UTOWN', 'PGP', 'bus', 12);
INSERT INTO `travel_times` VALUES (67, 'UTOWN', 'COM3', 'bus', 15);
INSERT INTO `travel_times` VALUES (68, 'UHC', 'UTOWN', 'bus', 4);
INSERT INTO `travel_times` VALUES (69, 'UHC', 'COM3', 'bus', 11);
INSERT INTO `travel_times` VALUES (70, 'LT27', 'UTOWN', 'bus', 6);
INSERT INTO `travel_times` VALUES (71, 'LT27', 'UHC', 'bus', 2);
INSERT INTO `travel_times` VALUES (72, 'LT27', 'COM3', 'bus', 9);
INSERT INTO `travel_times` VALUES (73, 'KRMRT', 'UTOWN', 'bus', 8);
INSERT INTO `travel_times` VALUES (74, 'KRMRT', 'UHC', 'bus', 4);
INSERT INTO `travel_times` VALUES (75, 'KRMRT', 'COM3', 'bus', 7);
INSERT INTO `travel_times` VALUES (76, 'PGP', 'UTOWN', 'bus', 12);
INSERT INTO `travel_times` VALUES (77, 'PGP', 'UHC', 'bus', 8);
INSERT INTO `travel_times` VALUES (78, 'PGP', 'COM3', 'bus', 3);
INSERT INTO `travel_times` VALUES (79, 'COM3', 'UTOWN', 'bus', 15);
INSERT INTO `travel_times` VALUES (80, 'COM3', 'UHC', 'bus', 11);
INSERT INTO `travel_times` VALUES (81, 'COM3', 'LT27', 'bus', 9);
INSERT INTO `travel_times` VALUES (82, 'COM3', 'KRMRT', 'bus', 7);
INSERT INTO `travel_times` VALUES (83, 'COM3', 'PGP', 'bus', 3);

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `full_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `hashed_password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `id`(`id`) USING BTREE,
  UNIQUE INDEX `email`(`email`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO `users` VALUES (1, 'test@example.com', 'Test User', '$2b$12$jKBFakyrX/dcQ6O/TwHE1uq3/LxU7Ao1XEL29B37/PuxmMlwnAgTy', 1, '2025-09-19 01:52:12', '2025-09-19 01:52:12');
INSERT INTO `users` VALUES (2, '123456@123.com', NULL, '$2b$12$sSd0OrMcImOh6CdOo.SKJOEGcwz2fsYek0zzP8nc.bv1aWpeZfCXe', 1, '2025-09-19 02:05:52', '2025-09-19 02:05:52');

SET FOREIGN_KEY_CHECKS = 1;
