#include "SifuModToolsLibrary.h"

#include "Modules/ModuleManager.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsAssetUtils.h"
#include "ClothingAsset.h"
#include "ClothingAssetFactory.h"
#include "ClothConfigNv.h"
#include "PointWeightMap.h"
#include "Animation/AnimInstance.h"
#include "AnimationRuntime.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "JsonObjectConverter.h"
#include "UObject/Package.h"
#include "AssetRegistryModule.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimNodeBase.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Kismet2/BlueprintEditorUtils.h"

class FSifuModToolsModule : public IModuleInterface {};
IMPLEMENT_MODULE(FSifuModToolsModule, SifuModTools)

namespace
{
	TSharedPtr<FJsonObject> ParseJson(const FString& Text)
	{
		TSharedPtr<FJsonObject> Obj;
		if (Text.IsEmpty())
		{
			return MakeShared<FJsonObject>();
		}
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		if (!FJsonSerializer::Deserialize(Reader, Obj))
		{
			return nullptr;
		}
		return Obj;
	}

	FVector ReadVec(const TSharedPtr<FJsonObject>& Obj, const FString& Key, const FVector& Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
		if (Obj->TryGetArrayField(Key, Arr) && Arr->Num() == 3)
		{
			return FVector((*Arr)[0]->AsNumber(), (*Arr)[1]->AsNumber(), (*Arr)[2]->AsNumber());
		}
		return Default;
	}

	FString TransformToJson(const FTransform& T)
	{
		const FVector L = T.GetLocation();
		const FQuat Q = T.GetRotation();
		const FVector S = T.GetScale3D();
		return FString::Printf(TEXT("\"t\":[%.6f,%.6f,%.6f],\"q\":[%.8f,%.8f,%.8f,%.8f],\"s\":[%.6f,%.6f,%.6f]"),
			L.X, L.Y, L.Z, Q.X, Q.Y, Q.Z, Q.W, S.X, S.Y, S.Z);
	}
}

namespace
{
	int32 FindSectionBySlot(USkeletalMesh* Mesh, const FString& Slot)
	{
		const FSkeletalMeshLODModel& Lod = Mesh->GetImportedModel()->LODModels[0];
		for (int32 i = 0; i < Lod.Sections.Num(); ++i)
		{
			const int32 Mat = Lod.Sections[i].MaterialIndex;
			if (Mesh->Materials.IsValidIndex(Mat) && Mesh->Materials[Mat].MaterialSlotName.ToString() == Slot)
			{
				return i;
			}
		}
		return INDEX_NONE;
	}

	FString FillMasks(UClothingAssetCommon* Asset, float MaxDistance, bool bAnimDrive, float BackstopScale = 0.f)
	{
		FClothLODDataCommon& ClothLod = Asset->LodData[0];
		FClothPhysicalMeshData& Phys = ClothLod.PhysicalMeshData;
		const int32 NumVerts = Phys.Vertices.Num();
		ClothLod.PointWeightMaps.Reset();
		ClothLod.PointWeightMaps.AddDefaulted();
		FPointWeightMap& MaxMask = ClothLod.PointWeightMaps.Last();
		MaxMask.Initialize(NumVerts);
		MaxMask.Name = TEXT("MaxDistance");
		MaxMask.CurrentTarget = (uint8)EWeightMapTargetCommon::MaxDistance;
		MaxMask.bEnabled = true;
		int32 NumFixed = 0;
		float MaxSeen = 0.f;
		for (int32 i = 0; i < NumVerts; ++i)
		{
			const FColor C = Phys.VertexColors.IsValidIndex(i) ? Phys.VertexColors[i] : FColor::Black;
			const float V = C.R / 255.f * MaxDistance;
			MaxMask.Values[i] = V;
			MaxSeen = FMath::Max(MaxSeen, V);
			NumFixed += V <= 0.1f ? 1 : 0;
		}
		if (bAnimDrive)
		{
			ClothLod.PointWeightMaps.AddDefaulted();
			FPointWeightMap& Drive = ClothLod.PointWeightMaps.Last();
			Drive.Initialize(NumVerts);
			Drive.Name = TEXT("AnimDrive");
			Drive.CurrentTarget = (uint8)EWeightMapTargetCommon::AnimDriveMultiplier;
			Drive.bEnabled = true;
			for (int32 i = 0; i < NumVerts; ++i)
			{
				const FColor C = Phys.VertexColors.IsValidIndex(i) ? Phys.VertexColors[i] : FColor::Black;
				Drive.Values[i] = C.G / 255.f;
			}
		}
		FString Backstop;
		if (BackstopScale > 0.f)
		{
			// Separation sphere centre = skinned position - distance * skinned normal, so the proxy normals must point
			// out of the body: count them against the horizontal direction from the proxy's centroid.
			FVector Centroid = FVector::ZeroVector;
			for (const FVector& P : Phys.Vertices)
			{
				Centroid += P;
			}
			Centroid /= FMath::Max(1, NumVerts);
			int32 NumOut = 0;
			for (int32 i = 0; i < NumVerts; ++i)
			{
				const FVector D = Phys.Vertices[i] - Centroid;
				NumOut += Phys.Normals.IsValidIndex(i) && Phys.Normals[i].X * D.X + Phys.Normals[i].Y * D.Y > 0.f ? 1 : 0;
			}
			ClothLod.PointWeightMaps.AddDefaulted(2);
			FPointWeightMap& Dist = ClothLod.PointWeightMaps[ClothLod.PointWeightMaps.Num() - 2];
			FPointWeightMap& Radius = ClothLod.PointWeightMaps.Last();
			Dist.Initialize(NumVerts);
			Dist.Name = TEXT("BackstopDistance");
			Dist.CurrentTarget = (uint8)EWeightMapTargetCommon::BackstopDistance;
			Dist.bEnabled = true;
			Radius.Initialize(NumVerts);
			Radius.Name = TEXT("BackstopRadius");
			Radius.CurrentTarget = (uint8)EWeightMapTargetCommon::BackstopRadius;
			Radius.bEnabled = true;
			int32 NumBackstop = 0;
			for (int32 i = 0; i < NumVerts; ++i)
			{
				const FColor C = Phys.VertexColors.IsValidIndex(i) ? Phys.VertexColors[i] : FColor::Black;
				Dist.Values[i] = C.G / 255.f * BackstopScale;
				Radius.Values[i] = C.B / 255.f * BackstopScale;
				NumBackstop += Radius.Values[i] > 0.f ? 1 : 0;
			}
			Backstop = FString::Printf(TEXT(" backstop=%d normals_out=%d"), NumBackstop, NumOut);
		}
		return FString::Printf(TEXT("verts=%d fixed=%d maxdist=%.2f%s"), NumVerts, NumFixed, MaxSeen, *Backstop);
	}
}

FString USifuModToolsLibrary::CreateClothProxy(USkeletalMesh* Mesh, const FString& ProxySlot, const FString& RenderSlot, const FString& Name,
	UPhysicsAsset* CollisionAsset, float MaxDistance, bool bAnimDrive, const FString& ConfigJson, float BackstopScale)
{
	if (!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.Num() == 0)
	{
		return TEXT("ERROR: invalid mesh");
	}
	TSharedPtr<FJsonObject> Config = ParseJson(ConfigJson);
	if (!Config.IsValid())
	{
		return TEXT("ERROR: bad config json");
	}
	FString Result;
	{
		// Same pattern as FPersonaMeshDetails::OnClothingSelectionChanged: defer the rebuild until the binding is
		// recorded in UserSectionsData, otherwise the LOD model rebuild drops it.
		FScopedSkeletalMeshPostEditChange ScopedPostEditChange(Mesh);
		Mesh->Modify();

		const int32 ProxySection = FindSectionBySlot(Mesh, ProxySlot);
		if (ProxySection == INDEX_NONE)
		{
			return FString::Printf(TEXT("ERROR: no section for proxy slot %s"), *ProxySlot);
		}
		FSkeletalMeshClothBuildParams Params;
		Params.AssetName = Name;
		Params.LodIndex = 0;
		Params.SourceSection = ProxySection;
		Params.bRemoveFromMesh = true;
		Params.PhysicsAsset = CollisionAsset;
		UClothingAssetFactory* Factory = GetMutableDefault<UClothingAssetFactory>();
		UClothingAssetCommon* Asset = Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params));
		if (!Asset)
		{
			return TEXT("ERROR: CreateFromSkeletalMesh failed (degenerate triangles?)");
		}
		Mesh->AddClothingAsset(Asset);
		if (UClothConfigNv* Nv = Asset->GetClothConfig<UClothConfigNv>())
		{
			if (Config->Values.Num() > 0 && !FJsonObjectConverter::JsonObjectToUStruct(Config.ToSharedRef(), UClothConfigNv::StaticClass(), Nv, 0, 0))
			{
				return TEXT("ERROR: config json did not apply");
			}
		}
		const FString MaskInfo = FillMasks(Asset, MaxDistance, bAnimDrive, BackstopScale);
		Asset->ApplyParameterMasks(false);  // push masks to the physical mesh before binding (Bind computes fixed verts)

		const int32 RenderSection = FindSectionBySlot(Mesh, RenderSlot);
		if (RenderSection == INDEX_NONE)
		{
			return FString::Printf(TEXT("ERROR: no section for render slot %s"), *RenderSlot);
		}
		FSkeletalMeshLODModel& LODModel = Mesh->GetImportedModel()->LODModels[0];
		const int32 OriginalIndex = LODModel.Sections[RenderSection].OriginalDataSectionIndex;
		if (!Asset->BindToSkeletalMesh(Mesh, 0, RenderSection, 0))
		{
			return TEXT("ERROR: BindToSkeletalMesh failed");
		}
		int32 AssetIndex = INDEX_NONE;
		Mesh->MeshClothingAssets.Find(Asset, AssetIndex);
		FSkelMeshSourceSectionUserData& UserData = LODModel.UserSectionsData.FindOrAdd(OriginalIndex);
		UserData.CorrespondClothAssetIndex = AssetIndex;
		UserData.ClothingData.AssetGuid = Asset->GetAssetGuid();
		UserData.ClothingData.AssetLodIndex = 0;
		Asset->CalculateReferenceBoneIndex();
		Result = FString::Printf(TEXT("ok %s %s render_section=%d original=%d asset_index=%d bones=%d"), *Asset->GetName(), *MaskInfo,
			RenderSection, OriginalIndex, AssetIndex, Asset->UsedBoneNames.Num());
	}
	Mesh->MarkPackageDirty();
	return Result;
}

FString USifuModToolsLibrary::CreateClothFromSection(USkeletalMesh* Mesh, int32 LodIndex, int32 SectionIndex, const FString& Name,
	UPhysicsAsset* CollisionAsset, float MaxDistance, bool bAnimDrive, const FString& ConfigJson)
{
	if (!Mesh || !Mesh->GetImportedModel() || !Mesh->GetImportedModel()->LODModels.IsValidIndex(LodIndex))
	{
		return TEXT("ERROR: invalid mesh or LOD");
	}
	FSkeletalMeshLODModel& LodModel = Mesh->GetImportedModel()->LODModels[LodIndex];
	if (!LodModel.Sections.IsValidIndex(SectionIndex))
	{
		return TEXT("ERROR: invalid section");
	}
	if (LodModel.Sections[SectionIndex].HasClothingData())
	{
		return TEXT("ERROR: section already has clothing");
	}
	TSharedPtr<FJsonObject> Config = ParseJson(ConfigJson);
	if (!Config.IsValid())
	{
		return TEXT("ERROR: bad config json");
	}

	Mesh->Modify();

	FSkeletalMeshClothBuildParams Params;
	Params.AssetName = Name;
	Params.LodIndex = LodIndex;
	Params.SourceSection = SectionIndex;
	Params.bRemoveFromMesh = false;
	Params.PhysicsAsset = CollisionAsset;

	UClothingAssetFactory* Factory = GetMutableDefault<UClothingAssetFactory>();
	UClothingAssetCommon* Asset = Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params));
	if (!Asset)
	{
		return TEXT("ERROR: CreateFromSkeletalMesh failed (degenerate triangles?)");
	}
	Mesh->AddClothingAsset(Asset);

	// Simulation config.
	if (UClothConfigNv* Nv = Asset->GetClothConfig<UClothConfigNv>())
	{
		if (Config->Values.Num() > 0 && !FJsonObjectConverter::JsonObjectToUStruct(Config.ToSharedRef(), UClothConfigNv::StaticClass(), Nv, 0, 0))
		{
			return TEXT("ERROR: config json did not apply");
		}
	}

	if (!Asset->BindToSkeletalMesh(Mesh, LodIndex, SectionIndex, 0))
	{
		return TEXT("ERROR: BindToSkeletalMesh failed");
	}

	// Masks from vertex colors.
	FClothLODDataCommon& ClothLod = Asset->LodData[0];
	FClothPhysicalMeshData& Phys = ClothLod.PhysicalMeshData;
	const int32 NumVerts = Phys.Vertices.Num();

	FPointWeightMap* MaxMask = nullptr;
	for (FPointWeightMap& Map : ClothLod.PointWeightMaps)
	{
		if (Map.CurrentTarget == (uint8)EWeightMapTargetCommon::MaxDistance)
		{
			MaxMask = &Map;
		}
	}
	if (!MaxMask)
	{
		ClothLod.PointWeightMaps.AddDefaulted();
		MaxMask = &ClothLod.PointWeightMaps.Last();
		MaxMask->Initialize(NumVerts);
		MaxMask->CurrentTarget = (uint8)EWeightMapTargetCommon::MaxDistance;
	}
	MaxMask->Name = TEXT("MaxDistance");
	MaxMask->bEnabled = true;
	MaxMask->Values.SetNumZeroed(NumVerts);

	int32 NumFixed = 0;
	float MaxSeen = 0.f;
	for (int32 i = 0; i < NumVerts; ++i)
	{
		const FColor C = Phys.VertexColors.IsValidIndex(i) ? Phys.VertexColors[i] : FColor::Black;
		const float V = C.R / 255.f * MaxDistance;
		MaxMask->Values[i] = V;
		MaxSeen = FMath::Max(MaxSeen, V);
		if (V <= 0.1f)
		{
			++NumFixed;
		}
	}

	if (bAnimDrive)
	{
		ClothLod.PointWeightMaps.AddDefaulted();
		FPointWeightMap& Drive = ClothLod.PointWeightMaps.Last();
		Drive.Initialize(NumVerts);
		Drive.Name = TEXT("AnimDrive");
		Drive.CurrentTarget = (uint8)EWeightMapTargetCommon::AnimDriveMultiplier;
		Drive.bEnabled = true;
		for (int32 i = 0; i < NumVerts; ++i)
		{
			const FColor C = Phys.VertexColors.IsValidIndex(i) ? Phys.VertexColors[i] : FColor::Black;
			Drive.Values[i] = C.G / 255.f;
		}
	}

	Asset->ApplyParameterMasks(true);
	Asset->CalculateReferenceBoneIndex();
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();

	return FString::Printf(TEXT("ok %s verts=%d fixed=%d maxdist=%.2f bones=%d"), *Asset->GetName(), NumVerts, NumFixed, MaxSeen, Asset->UsedBoneNames.Num());
}

int32 USifuModToolsLibrary::RemoveAllClothing(USkeletalMesh* Mesh)
{
	if (!Mesh)
	{
		return 0;
	}
	Mesh->Modify();
	TArray<UClothingAssetBase*> Assets = Mesh->MeshClothingAssets;
	for (UClothingAssetBase* Asset : Assets)
	{
		if (Asset)
		{
			Asset->UnbindFromSkeletalMesh(Mesh);
		}
	}
	Mesh->MeshClothingAssets.Empty();
	Mesh->PostEditChange();
	Mesh->MarkPackageDirty();
	return Assets.Num();
}

FString USifuModToolsLibrary::BuildPhysicsAsset(UPhysicsAsset* PA, USkeletalMesh* Mesh, const FString& Json)
{
	if (!PA || !Mesh)
	{
		return TEXT("ERROR: null asset");
	}
	TSharedPtr<FJsonObject> Root = ParseJson(Json);
	if (!Root.IsValid())
	{
		return TEXT("ERROR: bad json");
	}
	PA->Modify();
	while (PA->SkeletalBodySetups.Num() > 0)
	{
		FPhysicsAssetUtils::DestroyBody(PA, PA->SkeletalBodySetups.Num() - 1);
	}
	while (PA->ConstraintSetup.Num() > 0)
	{
		FPhysicsAssetUtils::DestroyConstraint(PA, PA->ConstraintSetup.Num() - 1);
	}

	const FReferenceSkeleton& Ref = Mesh->RefSkeleton;
	FPhysAssetCreateParams CreateParams;
	int32 Made = 0;
	const TArray<TSharedPtr<FJsonValue>>* Bodies = nullptr;
	if (Root->TryGetArrayField(TEXT("bodies"), Bodies))
	{
		for (const TSharedPtr<FJsonValue>& V : *Bodies)
		{
			TSharedPtr<FJsonObject> B = V->AsObject();
			const FName Bone(*B->GetStringField(TEXT("bone")));
			if (Ref.FindBoneIndex(Bone) == INDEX_NONE)
			{
				return FString::Printf(TEXT("ERROR: bone %s not in mesh"), *Bone.ToString());
			}
			const int32 Index = FPhysicsAssetUtils::CreateNewBody(PA, Bone, CreateParams);
			USkeletalBodySetup* Setup = PA->SkeletalBodySetups[Index];
			const FString Type = B->GetStringField(TEXT("type"));
			const FVector Center = ReadVec(B, TEXT("center"), FVector::ZeroVector);
			const FVector Rot = ReadVec(B, TEXT("rotation"), FVector::ZeroVector);
			FRotator Rotator(Rot.X, Rot.Y, Rot.Z);
			const TArray<TSharedPtr<FJsonValue>>* QuatArr = nullptr;
			if (B->TryGetArrayField(TEXT("quat"), QuatArr) && QuatArr->Num() == 4)
			{
				Rotator = FQuat((*QuatArr)[0]->AsNumber(), (*QuatArr)[1]->AsNumber(), (*QuatArr)[2]->AsNumber(), (*QuatArr)[3]->AsNumber()).GetNormalized().Rotator();
			}
			if (Type == TEXT("sphere"))
			{
				FKSphereElem E(B->GetNumberField(TEXT("radius")));
				E.Center = Center;
				Setup->AggGeom.SphereElems.Add(E);
			}
			else if (Type == TEXT("tapered"))
			{
				// NvCloth collides tapered capsules (sphere Radius0 at Center + Z * Length / 2, Radius1 at the other end)
				FKTaperedCapsuleElem E(B->GetNumberField(TEXT("radius0")), B->GetNumberField(TEXT("radius1")), B->GetNumberField(TEXT("length")));
				E.Center = Center;
				E.Rotation = Rotator;
				Setup->AggGeom.TaperedCapsuleElems.Add(E);
			}
			else if (Type == TEXT("box"))
			{
				const FVector Ext = ReadVec(B, TEXT("extent"), FVector(10, 10, 10));
				FKBoxElem E(Ext.X, Ext.Y, Ext.Z);
				E.Center = Center;
				E.Rotation = Rotator;
				Setup->AggGeom.BoxElems.Add(E);
			}
			else
			{
				FKSphylElem E(B->GetNumberField(TEXT("radius")), B->GetNumberField(TEXT("length")));
				E.Center = Center;
				E.Rotation = Rotator;
				Setup->AggGeom.SphylElems.Add(E);
			}
			bool bKinematic = true;
			B->TryGetBoolField(TEXT("kinematic"), bKinematic);
			Setup->PhysicsType = bKinematic ? PhysType_Kinematic : PhysType_Simulated;
			double Mass = 0.0;
			if (B->TryGetNumberField(TEXT("mass"), Mass) && Mass > 0.0)
			{
				Setup->DefaultInstance.bOverrideMass = true;
				Setup->DefaultInstance.SetMassOverride(Mass);
			}
			double Damp = 0.0;
			if (B->TryGetNumberField(TEXT("lin_damp"), Damp))
			{
				Setup->DefaultInstance.LinearDamping = Damp;
			}
			if (B->TryGetNumberField(TEXT("ang_damp"), Damp))
			{
				Setup->DefaultInstance.AngularDamping = Damp;
			}
			++Made;
		}
	}

	int32 Joints = 0;
	bool bConstraints = false;
	Root->TryGetBoolField(TEXT("constraints"), bConstraints);
	const TArray<TSharedPtr<FJsonValue>>* Explicit = nullptr;
	if (Root->TryGetArrayField(TEXT("joints"), Explicit))
	{
		TArray<FTransform> CS;
		FAnimationRuntime::FillUpComponentSpaceTransforms(Ref, Ref.GetRefBonePose(), CS);
		for (const TSharedPtr<FJsonValue>& V : *Explicit)
		{
			TSharedPtr<FJsonObject> J = V->AsObject();
			const FName Child(*J->GetStringField(TEXT("child")));
			const FName Parent(*J->GetStringField(TEXT("parent")));
			const int32 ChildBody = PA->FindBodyIndex(Child);
			const int32 ParentBody = PA->FindBodyIndex(Parent);
			if (ChildBody == INDEX_NONE || ParentBody == INDEX_NONE)
			{
				return FString::Printf(TEXT("ERROR: joint %s-%s has no bodies"), *Child.ToString(), *Parent.ToString());
			}
			const FTransform RelTM = CS[Ref.FindBoneIndex(Child)].GetRelativeTransform(CS[Ref.FindBoneIndex(Parent)]);
			const int32 CIdx = FPhysicsAssetUtils::CreateNewConstraint(PA, Child);
			UPhysicsConstraintTemplate* T = PA->ConstraintSetup[CIdx];
			FConstraintInstance& Inst = T->DefaultInstance;
			Inst.ConstraintBone1 = Child;
			Inst.Pos1 = FVector::ZeroVector;
			Inst.PriAxis1 = FVector(1, 0, 0);
			Inst.SecAxis1 = FVector(0, 1, 0);
			Inst.ConstraintBone2 = Parent;
			Inst.Pos2 = RelTM.GetLocation();
			Inst.PriAxis2 = RelTM.GetUnitAxis(EAxis::X);
			Inst.SecAxis2 = RelTM.GetUnitAxis(EAxis::Y);
			Inst.SetLinearXMotion(LCM_Locked);
			Inst.SetLinearYMotion(LCM_Locked);
			Inst.SetLinearZMotion(LCM_Locked);
			Inst.SetAngularSwing1Limit(ACM_Limited, J->GetNumberField(TEXT("swing1")));
			Inst.SetAngularSwing2Limit(ACM_Limited, J->GetNumberField(TEXT("swing2")));
			Inst.SetAngularTwistLimit(ACM_Limited, J->GetNumberField(TEXT("twist")));
			double Stiff = 0.0, DriveDamp = 0.0;
			J->TryGetNumberField(TEXT("drive_stiffness"), Stiff);
			J->TryGetNumberField(TEXT("drive_damping"), DriveDamp);
			if (Stiff > 0.0 || DriveDamp > 0.0)
			{
				Inst.SetAngularDriveMode(EAngularDriveMode::SLERP);
				Inst.SetOrientationDriveSLERP(true);
				Inst.SetAngularVelocityDriveSLERP(DriveDamp > 0.0);
				Inst.SetAngularDriveParams(Stiff, DriveDamp, 0.f);
				Inst.SetAngularOrientationTarget(FQuat::Identity);
			}
			T->SetDefaultProfile(Inst);
			PA->DisableCollision(ChildBody, ParentBody);
			++Joints;
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Pairs = nullptr;
	if (Root->TryGetArrayField(TEXT("disable_pairs"), Pairs))
	{
		for (const TSharedPtr<FJsonValue>& V : *Pairs)
		{
			const TArray<TSharedPtr<FJsonValue>>& P = V->AsArray();
			const int32 IA = PA->FindBodyIndex(FName(*P[0]->AsString()));
			const int32 IB = PA->FindBodyIndex(FName(*P[1]->AsString()));
			if (IA != INDEX_NONE && IB != INDEX_NONE)
			{
				PA->DisableCollision(IA, IB);
			}
		}
	}
	if (bConstraints)
	{
		TArray<FTransform> LocalPose = Ref.GetRefBonePose();
		for (int32 BodyIndex = 0; BodyIndex < PA->SkeletalBodySetups.Num(); ++BodyIndex)
		{
			const FName BoneName = PA->SkeletalBodySetups[BodyIndex]->BoneName;
			int32 BoneIndex = Ref.FindBoneIndex(BoneName);
			FTransform RelTM = FTransform::Identity;
			int32 ParentIndex = BoneIndex;
			int32 ParentBodyIndex = INDEX_NONE;
			FName ParentName;
			do
			{
				RelTM = RelTM * LocalPose[ParentIndex];
				ParentIndex = Ref.GetParentIndex(ParentIndex);
				if (ParentIndex == INDEX_NONE)
				{
					break;
				}
				ParentName = Ref.GetBoneName(ParentIndex);
				ParentBodyIndex = PA->FindBodyIndex(ParentName);
			} while (ParentBodyIndex == INDEX_NONE);

			if (ParentBodyIndex == INDEX_NONE)
			{
				continue;
			}
			const int32 CI = FPhysicsAssetUtils::CreateNewConstraint(PA, BoneName);
			UPhysicsConstraintTemplate* CS = PA->ConstraintSetup[CI];
			CS->DefaultInstance.SetAngularSwing1Motion(ACM_Limited);
			CS->DefaultInstance.SetAngularSwing2Motion(ACM_Limited);
			CS->DefaultInstance.SetAngularTwistMotion(ACM_Limited);
			CS->DefaultInstance.ConstraintBone1 = BoneName;
			CS->DefaultInstance.Pos1 = FVector::ZeroVector;
			CS->DefaultInstance.PriAxis1 = FVector(1, 0, 0);
			CS->DefaultInstance.SecAxis1 = FVector(0, 1, 0);
			CS->DefaultInstance.ConstraintBone2 = ParentName;
			CS->DefaultInstance.Pos2 = RelTM.GetLocation();
			CS->DefaultInstance.PriAxis2 = RelTM.GetUnitAxis(EAxis::X);
			CS->DefaultInstance.SecAxis2 = RelTM.GetUnitAxis(EAxis::Y);
			CS->SetDefaultProfile(CS->DefaultInstance);
			PA->DisableCollision(BodyIndex, ParentBodyIndex);
			++Joints;
		}
	}

	PA->UpdateBodySetupIndexMap();
	PA->UpdateBoundsBodiesArray();
	PA->SetPreviewMesh(Mesh);
	PA->PostEditChange();
	PA->MarkPackageDirty();
	return FString::Printf(TEXT("ok bodies=%d constraints=%d"), Made, Joints);
}

UPhysicsAsset* USifuModToolsLibrary::CreatePhysicsAsset(const FString& PackagePath, const FString& Name, USkeletalMesh* PreviewMesh)
{
	const FString LongName = PackagePath / Name;
	if (UPhysicsAsset* Existing = LoadObject<UPhysicsAsset>(nullptr, *(LongName + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		return Existing;
	}
	UPackage* Package = CreatePackage(*LongName);
	UPhysicsAsset* PA = NewObject<UPhysicsAsset>(Package, *Name, RF_Public | RF_Standalone | RF_Transactional);
	if (PreviewMesh)
	{
		PA->SetPreviewMesh(PreviewMesh);
	}
	FAssetRegistryModule::AssetCreated(PA);
	PA->MarkPackageDirty();
	return PA;
}

namespace
{
	UEdGraphNode* SpawnAnimNode(UEdGraph* Graph, const TCHAR* ClassName, int32 X)
	{
		UClass* Cls = FindObject<UClass>(ANY_PACKAGE, ClassName);
		if (!Cls)
		{
			return nullptr;
		}
		UEdGraphNode* Node = NewObject<UEdGraphNode>(Graph, Cls, NAME_None, RF_Transactional);
		Graph->AddNode(Node, false, false);
		Node->CreateNewGuid();
		Node->PostPlacedNewNode();
		Node->AllocateDefaultPins();
		Node->NodePosX = X;
		Node->NodePosY = 0;
		return Node;
	}

	bool IsPosePin(const UEdGraphPin* Pin)
	{
		const UObject* Sub = Pin->PinType.PinSubCategoryObject.Get();
		return Sub == FPoseLink::StaticStruct() || Sub == FComponentSpacePoseLink::StaticStruct();
	}

	UEdGraphPin* FindPosePin(UEdGraphNode* Node, EEdGraphPinDirection Dir)
	{
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin->Direction == Dir && IsPosePin(Pin))
			{
				return Pin;
			}
		}
		return nullptr;
	}
}

FString USifuModToolsLibrary::SetupRigidBodyPostProcess(UAnimBlueprint* AnimBP, const FString& RigidBodyJson)
{
	if (!AnimBP)
	{
		return TEXT("ERROR: null anim blueprint");
	}
	TSharedPtr<FJsonObject> Settings = ParseJson(RigidBodyJson);
	if (!Settings.IsValid())
	{
		return TEXT("ERROR: bad json");
	}
	UEdGraph* Graph = nullptr;
	for (UEdGraph* G : AnimBP->FunctionGraphs)
	{
		if (G && G->GetFName() == TEXT("AnimGraph"))
		{
			Graph = G;
		}
	}
	if (!Graph)
	{
		return TEXT("ERROR: no AnimGraph");
	}
	UEdGraphNode* RootNode = nullptr;
	for (UEdGraphNode* N : TArray<UEdGraphNode*>(Graph->Nodes))
	{
		if (N->GetClass()->GetName() == TEXT("AnimGraphNode_Root"))
		{
			RootNode = N;
		}
		else
		{
			N->BreakAllNodeLinks();
			Graph->RemoveNode(N);
		}
	}
	if (!RootNode)
	{
		return TEXT("ERROR: no root node");
	}
	UEdGraphNode* InPose = SpawnAnimNode(Graph, TEXT("AnimGraphNode_LinkedInputPose"), -1200);
	UEdGraphNode* ToCS = SpawnAnimNode(Graph, TEXT("AnimGraphNode_LocalToComponentSpace"), -900);
	UEdGraphNode* RB = SpawnAnimNode(Graph, TEXT("AnimGraphNode_RigidBody"), -600);
	UEdGraphNode* ToLS = SpawnAnimNode(Graph, TEXT("AnimGraphNode_ComponentToLocalSpace"), -300);
	if (!InPose || !ToCS || !RB || !ToLS)
	{
		return TEXT("ERROR: could not spawn anim graph nodes");
	}
	FStructProperty* NodeProp = FindFProperty<FStructProperty>(RB->GetClass(), TEXT("Node"));
	if (!NodeProp)
	{
		return TEXT("ERROR: RigidBody node struct not found");
	}
	if (!FJsonObjectConverter::JsonObjectToUStruct(Settings.ToSharedRef(), NodeProp->Struct, NodeProp->ContainerPtrToValuePtr<void>(RB), 0, 0))
	{
		return TEXT("ERROR: rigid body settings did not apply");
	}
	const UEdGraphSchema* Schema = Graph->GetSchema();
	auto Link = [&](UEdGraphNode* A, UEdGraphNode* B) -> bool
	{
		UEdGraphPin* Out = FindPosePin(A, EGPD_Output);
		UEdGraphPin* In = FindPosePin(B, EGPD_Input);
		return Out && In && Schema->TryCreateConnection(Out, In);
	};
	if (!Link(InPose, ToCS) || !Link(ToCS, RB) || !Link(RB, ToLS) || !Link(ToLS, RootNode))
	{
		return TEXT("ERROR: pose pin connection failed");
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);
	FKismetEditorUtilities::CompileBlueprint(AnimBP);
	AnimBP->MarkPackageDirty();
	return FString::Printf(TEXT("ok status=%d nodes=%d"), (int32)AnimBP->Status, Graph->Nodes.Num());
}

FString USifuModToolsLibrary::DumpRefSkeleton(USkeletalMesh* Mesh)
{
	if (!Mesh)
	{
		return TEXT("[]");
	}
	const FReferenceSkeleton& Ref = Mesh->RefSkeleton;
	const TArray<FTransform>& Pose = Ref.GetRefBonePose();
	FString Out = TEXT("[");
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		Out += FString::Printf(TEXT("%s{\"name\":\"%s\",\"parent\":%d,%s}"), i ? TEXT(",") : TEXT(""),
			*Ref.GetBoneName(i).ToString(), Ref.GetParentIndex(i), *TransformToJson(Pose[i]));
	}
	return Out + TEXT("]");
}

FString USifuModToolsLibrary::DumpSections(USkeletalMesh* Mesh)
{
	if (!Mesh || !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.Num() == 0)
	{
		return TEXT("[]");
	}
	const FSkeletalMeshLODModel& Lod = Mesh->GetImportedModel()->LODModels[0];
	FString Out = TEXT("{\"sections\":[");
	for (int32 i = 0; i < Lod.Sections.Num(); ++i)
	{
		const FSkelMeshSection& S = Lod.Sections[i];
		const FName Slot = Mesh->Materials.IsValidIndex(S.MaterialIndex) ? Mesh->Materials[S.MaterialIndex].MaterialSlotName : NAME_None;
		Out += FString::Printf(TEXT("%s{\"section\":%d,\"material\":%d,\"slot\":\"%s\",\"verts\":%d,\"tris\":%d,\"bones\":%d,\"cloth\":\"%s\",\"disabled\":%d,\"cloth_index\":%d,\"mapping\":%d}"),
			i ? TEXT(",") : TEXT(""), i, S.MaterialIndex, *Slot.ToString(), S.GetNumVertices(), S.NumTriangles, S.BoneMap.Num(),
			*S.ClothingData.AssetGuid.ToString(), S.bDisabled ? 1 : 0, (int32)S.CorrespondClothAssetIndex, S.ClothMappingData.Num());
	}
	Out += TEXT("],\"assets\":[");
	for (int32 i = 0; i < Mesh->MeshClothingAssets.Num(); ++i)
	{
		UClothingAssetCommon* A = Cast<UClothingAssetCommon>(Mesh->MeshClothingAssets[i]);
		Out += FString::Printf(TEXT("%s{\"name\":\"%s\",\"guid\":\"%s\",\"lodmap\":%d,\"pa\":\"%s\"}"), i ? TEXT(",") : TEXT(""),
			A ? *A->GetName() : TEXT("null"), A ? *A->GetAssetGuid().ToString() : TEXT(""), A ? A->LodMap.Num() : -1,
			(A && A->PhysicsAsset) ? *A->PhysicsAsset->GetPathName() : TEXT(""));
	}
	return Out + TEXT("]}");
}

void USifuModToolsLibrary::SetPostProcessAnimBlueprint(USkeletalMesh* Mesh, UClass* AnimClass)
{
	if (!Mesh)
	{
		return;
	}
	Mesh->Modify();
	Mesh->PostProcessAnimBlueprint = AnimClass;
	Mesh->MarkPackageDirty();
}
