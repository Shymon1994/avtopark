-- Додавання виробників
INSERT OR IGNORE INTO manufacturers (name) VALUES
('Toyota'),
('Volkswagen'),
('BMW'),
('Mercedes-Benz'),
('Audi'),
('Honda'),
('Ford'),
('Hyundai'),
('Kia'),
('Tesla'),
('Nissan'),
('Chevrolet'),
('Porsche'),
('Subaru'),
('Mazda'),
('Lexus'),
('Volvo'),
('Renault'),
('Peugeot'),
('Skoda'),
('Citroën'),
('Opel'),
('Mitsubishi'),
('Jaguar'),
('Land Rover');

-- Додавання моделей
INSERT OR IGNORE INTO models (manufacturer_id, name) VALUES
(1, 'Camry'), (1, 'Corolla'), (1, 'RAV4'), (1, 'Prius'), (1, 'Highlander'), (1, 'Yaris'), (1, 'Avalon'), (1, 'Sienna'),
(2, 'Golf'), (2, 'Tiguan'), (2, 'Passat'), (2, 'Polo'), (2, 'Jetta'), (2, 'Arteon'), (2, 'ID.4'), (2, 'T-Roc'),
(3, '3 Series'), (3, '5 Series'), (3, 'X5'), (3, 'M3'), (3, 'X3'), (3, '7 Series'), (3, '4 Series'), (3, 'Z4'),
(4, 'C-Class'), (4, 'E-Class'), (4, 'S-Class'), (4, 'GLC'), (4, 'Sprinter'), (4, 'Citan'), (4, 'A-Class'), (4, 'GLA'),
(5, 'A4'), (5, 'Q5'), (5, 'A6'), (5, 'Q7'), (5, 'A3'), (5, 'Q3'), (5, 'e-tron'), (5, 'TT'),
(6, 'Civic'), (6, 'Accord'), (6, 'CR-V'), (6, 'Fit'), (6, 'Pilot'), (6, 'Odyssey'), (6, 'HR-V'), (6, 'Ridgeline'),
(7, 'F-150'), (7, 'Mustang'), (7, 'Focus'), (7, 'Explorer'), (7, 'Transit'), (7, 'Bronco'), (7, 'Escape'), (7, 'Ranger'),
(8, 'Tucson'), (8, 'Santa Fe'), (8, 'Elantra'), (8, 'Kona'), (8, 'Palisade'), (8, 'Ioniq'), (8, 'Venue'), (8, 'Nexo'),
(9, 'Optima'), (9, 'Sportage'), (9, 'Sorento'), (9, 'Rio'), (9, 'Telluride'), (9, 'Forte'), (9, 'Seltos'), (9, 'Stinger'),
(10, 'Model S'), (10, 'Model 3'), (10, 'Model X'), (10, 'Model Y'), (10, 'Cybertruck'), (10, 'Roadster'),
(11, 'Leaf'), (11, 'Rogue'), (11, 'Altima'), (11, 'Qashqai'), (11, 'Sentra'), (11, 'Pathfinder'), (11, 'Murano'), (11, 'Kicks'),
(12, 'Camaro'), (12, 'Equinox'), (12, 'Silverado'), (12, 'Malibu'), (12, 'Blazer'), (12, 'Traverse'), (12, 'Trax'), (12, 'Bolt'),
(13, '911'), (13, 'Cayenne'), (13, 'Panamera'), (13, 'Macan'), (13, 'Taycan'), (13, 'Boxster'), (13, 'Cayman'),
(14, 'Forester'), (14, 'Outback'), (14, 'Impreza'), (14, 'WRX'), (14, 'Crosstrek'), (14, 'Ascent'), (14, 'Legacy'),
(15, 'Mazda3'), (15, 'Mazda6'), (15, 'CX-5'), (15, 'MX-5'), (15, 'CX-30'), (15, 'CX-9'), (15, 'CX-3'),
(16, 'RX'), (16, 'ES'), (16, 'NX'), (16, 'LX'), (16, 'IS'), (16, 'GX'), (16, 'UX'), (16, 'LS'),
(17, 'XC60'), (17, 'XC90'), (17, 'S60'), (17, 'V90'), (17, 'S90'), (17, 'XC40'), (17, 'V60'),
(18, 'Clio'), (18, 'Megane'), (18, 'Captur'), (18, 'Duster'), (18, 'Trafic'), (18, 'Kangoo'), (18, 'Zoe'), (18, 'Talisman'),
(19, '208'), (19, '308'), (19, '3008'), (19, '5008'), (19, 'Partner'), (19, 'Boxer'), (19, '2008'), (19, 'Rifter'),
(20, 'Octavia'), (20, 'Superb'), (20, 'Kodiaq'), (20, 'Fabia'), (20, 'Karoq'), (20, 'Scala'), (20, 'Kamiq'),
(21, 'C3'), (21, 'C4'), (21, 'Berlingo'), (21, 'Jumpy'), (21, 'C5 Aircross'), (21, 'SpaceTourer'), (21, 'C3 Aircross'),
(22, 'Corsa'), (22, 'Astra'), (22, 'Insignia'), (22, 'Crossland'), (22, 'Grandland'), (22, 'Mokka'), (22, 'Combo'),
(23, 'Outlander'), (23, 'ASX'), (23, 'Eclipse Cross'), (23, 'Pajero'), (23, 'L200'), (23, 'Mirage'),
(24, 'F-Pace'), (24, 'XE'), (24, 'XF'), (24, 'I-Pace'), (24, 'E-Pace'), (24, 'F-Type'),
(25, 'Range Rover'), (25, 'Discovery'), (25, 'Defender'), (25, 'Range Rover Sport'), (25, 'Discovery Sport'), (25, 'Range Rover Evoque');

-- Додавання "Unknown" виробника та моделі
INSERT OR IGNORE INTO manufacturers (name) VALUES ('Unknown');
INSERT OR IGNORE INTO models (manufacturer_id, name) VALUES ((SELECT id FROM manufacturers WHERE name = 'Unknown'), 'Unknown');