/****** Object:  Table [Final].[Stores]    Script Date: 2/25/2026 2:58:22 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [Final].[Stores](
	[StoreID] [int] NOT NULL,
	[StoreName] [nvarchar](255) NOT NULL,
	[StoreAddress] [nvarchar](255) NOT NULL,
	[City] [nvarchar](50) NOT NULL,
	[StProv] [nvarchar](50) NOT NULL,
	[Country] [nvarchar](50) NOT NULL,
	[Status] [nvarchar](50) NOT NULL,
	[SiteType] [nvarchar](50) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[StoreID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

